# -*- coding: utf-8 -*-
# Author: cnr437@gmail.com
# Code URL: http://code.activestate.com/recipes/577231-discrete-pid-controller/
# License: MIT
# Modified by Openroast.


class PID(object):
    """Discrete PID control."""
    def __init__(self, P, I, D, Derivator=0, Integrator=0,
                 Output_max=8, Output_min=0):
        self.Kp = P
        self.Ki = I
        self.Kd = D
        self.Derivator = Derivator
        self.Integrator = Integrator
        self.Output_max = Output_max
        self.Output_min = Output_min
        if(I > 0.0):
            self.Integrator_max = Output_max / I
            self.Integrator_min = Output_min / I
        else:
            self.Integrator_max = 0.0
            self.Integrator_min = 0.0
        self.targetTemp = 0
        self.error = 0.0

    def update(self, currentTemp, targetTemp):
        """Calculate PID output value for given reference input and feedback."""
        # in this implementation, ki includes the dt multiplier term,
        # and kd includes the dt divisor term.  This is typical practice in
        # industry.
        self.targetTemp = targetTemp
        self.error = targetTemp - currentTemp

        self.P_value = self.Kp * self.error
        # it is common practice to compute derivative term against PV,
        # instead of de/dt.  This is because de/dt spikes
        # when the set point changes.

        # PV version with no dPV/dt filter - note 'previous'-'current',
        # that's desired, how the math works out
        self.D_value = self.Kd * (self.Derivator - currentTemp)
        self.Derivator = currentTemp

        self.Integrator = self.Integrator + self.error
        if self.Integrator > self.Integrator_max:
            self.Integrator = self.Integrator_max
        elif self.Integrator < self.Integrator_min:
            self.Integrator = self.Integrator_min

        self.I_value = self.Integrator * self.Ki

        output = self.P_value + self.I_value + self.D_value
        if output > self.Output_max:
            output = self.Output_max
        if output < self.Output_min:
            output = self.Output_min
        return(output)

    def setPoint(self, targetTemp):
        """Initilize the setpoint of PID."""
        self.targetTemp = targetTemp
        self.Integrator = 0
        self.Derivator = 0

    def setIntegrator(self, Integrator):
        self.Integrator = Integrator

    def setDerivator(self, Derivator):
        self.Derivator = Derivator

    def setKp(self, P):
        self.Kp = P

    def setKi(self, I):
        self.Ki = I

    def setKd(self, D):
        self.Kd = D

    def getPoint(self):
        return self.targetTemp

    def getError(self):
        return self.error

    def getIntegrator(self):
        return self.Integrator

    def getDerivator(self):
        return self.Derivator

    def update_p(self, p):
        self.Kp = p

    def update_i(self, i):
        self.Ki = i

    def update_d(self, d):
        self.Kd = d
