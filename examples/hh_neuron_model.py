# Copyright 2024 BDP Ecosystem Limited. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

import jax
import jax.numpy as jnp
import matplotlib.pyplot as plt

import brainunit as bu
import brainstate as bst

bst.environ.set(dt=0.01)


class HHWithEuler(bst.Dynamics):

  def __init__(self, size, keep_size: bool = False, ENa=50., gNa=120., EK=-77.,
               gK=36., EL=-54.387, gL=0.03, V_th=20., C=1.0):
    # initialization
    super().__init__(size=size, keep_size=keep_size, )

    # parameters
    self.ENa = ENa
    self.EK = EK
    self.EL = EL
    self.gNa = gNa
    self.gK = gK
    self.gL = gL
    self.C = C
    self.V_th = V_th

  # m channel
  m_alpha = lambda self, V: 1. / bu.math.exprel(-(V + 40) / 10)
  m_beta = lambda self, V: 4.0 * jnp.exp(-(V + 65) / 18)
  m_inf = lambda self, V: self.m_alpha(V) / (self.m_alpha(V) + self.m_beta(V))
  dm = lambda self, m, t, V: self.m_alpha(V) * (1 - m) - self.m_beta(V) * m

  # h channel
  h_alpha = lambda self, V: 0.07 * jnp.exp(-(V + 65) / 20.)
  h_beta = lambda self, V: 1 / (1 + jnp.exp(-(V + 35) / 10))
  h_inf = lambda self, V: self.h_alpha(V) / (self.h_alpha(V) + self.h_beta(V))
  dh = lambda self, h, t, V: self.h_alpha(V) * (1 - h) - self.h_beta(V) * h

  # n channel
  n_alpha = lambda self, V: 0.1 / bu.math.exprel(-(V + 55) / 10)
  n_beta = lambda self, V: 0.125 * jnp.exp(-(V + 65) / 80)
  n_inf = lambda self, V: self.n_alpha(V) / (self.n_alpha(V) + self.n_beta(V))
  dn = lambda self, n, t, V: self.n_alpha(V) * (1 - n) - self.n_beta(V) * n

  def init_state(self, batch_size=None):
    self.V = bst.State(jnp.ones(self.varshape, bst.environ.dftype()))
    self.m = bst.State(self.m_inf(self.V.value))
    self.h = bst.State(self.h_inf(self.V.value))
    self.n = bst.State(self.n_inf(self.V.value))
    self.spike = bst.State(jnp.zeros(self.varshape, bool))

  def dV(self, V, t, m, h, n, I):
    I = self.sum_current_inputs(V, init=I)
    I_Na = (self.gNa * m * m * m * h) * (V - self.ENa)
    n2 = n * n
    I_K = (self.gK * n2 * n2) * (V - self.EK)
    I_leak = self.gL * (V - self.EL)
    dVdt = (- I_Na - I_K - I_leak + I) / self.C
    return dVdt

  def update(self, x=0.):
    t = bst.environ.get('t')
    V = bst.nn.exp_euler_step(self.dV, self.V.value, t, self.m.value, self.h.value, self.n.value, x)
    m = bst.nn.exp_euler_step(self.dm, self.m.value, t, self.V.value)
    h = bst.nn.exp_euler_step(self.dh, self.h.value, t, self.V.value)
    n = bst.nn.exp_euler_step(self.dn, self.n.value, t, self.V.value)
    V += self.sum_delta_inputs()
    self.spike.value = jnp.logical_and(self.V.value < self.V_th, V >= self.V_th)
    self.V.value = V
    self.m.value = m
    self.h.value = h
    self.n.value = n
    return self.spike.value

  def update_return_info(self):
    return jax.ShapeDtypeStruct(self.varshape, bst.environ.dftype())

  def update_return(self):
    return self.spike.value


hh = HHWithEuler(10)
bst.init_states(hh)


def run(i, inp):
  with bst.environ.context(i=i, t=i * bst.environ.get_dt()):
    hh(inp)
  return hh.V.value


n = 10000
indices = jnp.arange(n)
vs = bst.transform.for_loop(run, indices, bst.random.uniform(1., 10., n),
                            pbar=bst.transform.ProgressBar(count=10))

plt.plot(indices * bst.environ.get_dt(), vs)
plt.show()
