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

from typing import Optional

from brainstate._module import (Module, Projection, Dynamics, ReceiveInputProj)
from brainstate._utils import set_module_as
from brainstate.mixin import (BindCondData, Mode)
from ._utils import is_instance

__all__ = [
  'VanillaProj',
]


@set_module_as('brainstate.nn')
class VanillaProj(Projection):
  """Synaptic projection which defines the synaptic computation with the dimension of pre-synaptic neuron group.

  **Code Examples**

  To simulate an E/I balanced network model:

  .. code-block::

      class EINet(bp.DynSysGroup):
        def __init__(self):
          super().__init__()
          self.N = bp.dyn.LifRef(4000, V_rest=-60., V_th=-50., V_reset=-60., tau=20., tau_ref=5.,
                                 V_initializer=bp.init.Normal(-55., 2.))
          self.delay = bp.VarDelay(self.N.spike, entries={'I': None})
          self.syn1 = bp.dyn.Expon(size=3200, tau=5.)
          self.syn2 = bp.dyn.Expon(size=800, tau=10.)
          self.E = bp.dyn.VanillaProj(comm=bp.dnn.JitFPHomoLinear(3200, 4000, prob=0.02, weight=0.6),
                                      out=bp.dyn.COBA(E=0.),
                                      post=self.N)
          self.I = bp.dyn.VanillaProj(comm=bp.dnn.JitFPHomoLinear(800, 4000, prob=0.02, weight=6.7),
                                      out=bp.dyn.COBA(E=-80.),
                                      post=self.N)

        def update(self, input):
          spk = self.delay.at('I')
          self.E(self.syn1(spk[:3200]))
          self.I(self.syn2(spk[3200:]))
          self.delay(self.N(input))
          return self.N.spike.value

      model = EINet()
      indices = bm.arange(1000)
      spks = bm.for_loop(lambda i: model.step_run(i, 20.), indices)
      bp.visualize.raster_plot(indices, spks, show=True)


  Args:
    comm: The synaptic communication.
    out: The synaptic output.
    post: The post-synaptic neuron group.
    name: str. The projection name.
    mode: Mode. The computing mode.
  """

  _invisible_nodes = ['post', ]

  def __init__(
      self,
      comm: Module,
      out: BindCondData,
      post: ReceiveInputProj,
      name: Optional[str] = None,
      mode: Optional[Mode] = None,
  ):
    super().__init__(name=name, mode=mode)

    # synaptic models
    is_instance(comm, Module)
    is_instance(out, BindCondData)
    is_instance(post, Dynamics)
    self.comm = comm

    # output initialization
    post.add_input_fun(self.name, out)
    self.out = out

    self.post = post

  def update(self, x):
    current = self.comm(x)
    self.out.bind_cond(current)
    return current
