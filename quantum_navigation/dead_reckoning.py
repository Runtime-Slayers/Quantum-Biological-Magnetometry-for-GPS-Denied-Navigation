import numpy as np

def dead_reckoning_nav(B_field_sequence, dt=0.1, heading_init=0.0):
    headings = [heading_init]
    for i in range(1, len(B_field_sequence)):
        delta_B = B_field_sequence[i] - B_field_sequence[i-1]
        d_heading = np.degrees(np.arctan2(delta_B[1], delta_B[0]))
        headings.append(headings[-1] + d_heading * dt)
    return np.array(headings)

class QuantumNavigationEKF:
    """
    10D Extended Kalman Filter (EKF) for fusing noisy IMU dead reckoning
    with 3D NV-Diamond magnetometry and biological spin compass yield,
    dynamically estimating local magnetic anomaly vector in Earth frame.
    
    State vector x:
      x[0:3] = 3D Position (p_x, p_y, p_z)
      x[3:6] = 3D Velocity (v_x, v_y, v_z)
      x[6]   = Heading angle theta (radians)
      x[7:10] = 3D Magnetic Anomaly vector in Earth frame (B_anom_x, B_anom_y, B_anom_z)
    """
    def __init__(self, x_init=None, P_init=None, B_earth_vector=None):
        if B_earth_vector is None:
            self.B0 = np.array([30e-6, 10e-6, -40e-6])
        else:
            self.B0 = np.array(B_earth_vector)
            
        if x_init is None:
            self.x = np.zeros(10)
        else:
            if len(x_init) == 7:
                self.x = np.zeros(10)
                self.x[0:7] = x_init
            else:
                self.x = np.array(x_init, dtype=float)
            
        if P_init is None:
            self.P = np.eye(10) * 0.1
            self.P[7:10, 7:10] = np.eye(3) * 1e-12
        else:
            if len(P_init) == 7:
                self.P = np.eye(10) * 0.1
                self.P[0:7, 0:7] = P_init
                self.P[7:10, 7:10] = np.eye(3) * 1e-12
            else:
                self.P = np.array(P_init, dtype=float)
            
        # Extended process noise covariance Q (10 x 10)
        self.Q = np.diag([0.01, 0.01, 0.01, 0.05, 0.05, 0.05, 0.001, 1e-13, 1e-13, 1e-13])
        
    def predict(self, a_body, omega_heading, dt=0.1):
        """
        Propagates state and covariance.
        """
        theta = self.x[6]
        
        # Heading propagation
        theta_new = (theta + omega_heading * dt) % (2 * np.pi)
        
        cos_t = np.cos(theta_new)
        sin_t = np.sin(theta_new)
        R = np.array([
            [cos_t, -sin_t, 0.0],
            [sin_t,  cos_t, 0.0],
            [0.0,    0.0,   1.0]
        ])
        
        g = np.array([0.0, 0.0, 9.81])
        a_earth = R.dot(a_body) - g
        
        p = self.x[0:3]
        v = self.x[3:6]
        B_anom = self.x[7:10]
        
        v_new = v + a_earth * dt
        p_new = p + v * dt + 0.5 * a_earth * dt**2
        B_anom_new = B_anom
        
        self.x[0:3] = p_new
        self.x[3:6] = v_new
        self.x[6] = theta_new
        self.x[7:10] = B_anom_new
        
        # Jacobian of transition matrix F (10 x 10):
        F = np.eye(10)
        F[0:3, 3:6] = np.eye(3) * dt
        
        dR_dtheta = np.array([
            [-sin_t, -cos_t, 0.0],
            [ cos_t, -sin_t, 0.0],
            [0.0,    0.0,    0.0]
        ])
        da_dtheta = dR_dtheta.dot(a_body)
        
        F[3:6, 6] = da_dtheta * dt
        F[0:3, 6] = 0.5 * da_dtheta * dt**2
        
        self.P = F.dot(self.P).dot(F.T) + self.Q
        
    def update_magnetometer(self, B_meas, R_cov=None):
        """
        EKF measurement update using noisy 3D NV-Diamond magnetic vector in body frame.
        """
        if R_cov is None:
            R_cov = np.eye(3) * 1e-12
            
        theta = self.x[6]
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)
        
        R = np.array([
            [cos_t, -sin_t, 0.0],
            [sin_t,  cos_t, 0.0],
            [0.0,    0.0,   1.0]
        ])
        
        B_total = self.B0 + self.x[7:10]
        B_pred = R.T.dot(B_total)
        
        # Jacobian H1 (3 x 10)
        dh_dtheta = np.array([
           -B_total[0] * sin_t + B_total[1] * cos_t,
           -B_total[0] * cos_t - B_total[1] * sin_t,
            0.0
        ])
        
        H = np.zeros((3, 10))
        H[:, 6] = dh_dtheta
        H[:, 7:10] = R.T
        
        S = H.dot(self.P).dot(H.T) + R_cov
        K = self.P.dot(H.T).dot(np.linalg.inv(S))
        
        y = B_meas - B_pred
        self.x = self.x + K.dot(y)
        self.x[6] = self.x[6] % (2 * np.pi)
        self.P = (np.eye(10) - K.dot(H)).dot(self.P)
        
    def update_radical_pair(self, Y_meas, R_cov=1e-6):
        """
        EKF measurement update using noisy radical pair singlet yield.
        """
        from quantum_navigation.sensors import radical_pair_singlet_yield
        
        theta = self.x[6]
        
        # Measurement function h_2(x)
        def h_2(t, B_anom):
            cos_t = np.cos(t)
            sin_t = np.sin(t)
            B_total = self.B0 + B_anom
            B_body = np.array([
                B_total[0] * cos_t + B_total[1] * sin_t,
               -B_total[0] * sin_t + B_total[1] * cos_t,
                B_total[2]
            ])
            return radical_pair_singlet_yield(B_body, noise_std=0.0)
            
        Y_pred = h_2(theta, self.x[7:10])
        
        # Numerical Jacobian H2 (1 x 10)
        delta = 1e-5
        dY_dtheta = (h_2(theta + delta, self.x[7:10]) - h_2(theta - delta, self.x[7:10])) / (2 * delta)
        
        dY_dAnom = []
        for i in range(3):
            anom_plus = self.x[7:10].copy()
            anom_plus[i] += delta
            anom_minus = self.x[7:10].copy()
            anom_minus[i] -= delta
            dY_dAnom.append((h_2(theta, anom_plus) - h_2(theta, anom_minus)) / (2 * delta))
            
        H = np.zeros((1, 10))
        H[0, 6] = dY_dtheta
        H[0, 7:10] = dY_dAnom
        
        S = H.dot(self.P).dot(H.T) + R_cov
        K = self.P.dot(H.T) / S[0, 0]
        
        y = Y_meas - Y_pred
        self.x = self.x + K.squeeze() * y
        self.x[6] = self.x[6] % (2 * np.pi)
        self.P = (np.eye(10) - K.dot(H)).dot(self.P)
