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

import unittest

import jax
import jax.numpy as jnp
import pytest

import brainstate as bc


class TestMakeJaxpr(unittest.TestCase):

  def test_compar_jax_make_jaxpr(self):
    def func4(arg):  # Arg is a pair
      temp = arg[0] + jnp.sin(arg[1]) * 3.
      c = bc.random.rand_like(arg[0])
      return jnp.sum(temp + c)

    key = bc.random.DEFAULT.value
    jaxpr = jax.make_jaxpr(func4)((jnp.zeros(8), jnp.ones(8)))
    print(jaxpr)
    self.assertTrue(len(jaxpr.in_avals) == 2)
    self.assertTrue(len(jaxpr.consts) == 1)
    self.assertTrue(len(jaxpr.out_avals) == 1)
    self.assertTrue(jnp.allclose(jaxpr.consts[0], key))

    jaxpr2, states = bc.transform.make_jaxpr(func4)((jnp.zeros(8), jnp.ones(8)))
    print(jaxpr2)
    self.assertTrue(len(jaxpr2.in_avals) == 3)
    self.assertTrue(len(jaxpr2.out_avals) == 2)
    self.assertTrue(len(jaxpr2.consts) == 0)

  def test_StatefulFunction_1(self):
    def func4(arg):  # Arg is a pair
      temp = arg[0] + jnp.sin(arg[1]) * 3.
      c = bc.random.rand_like(arg[0])
      return jnp.sum(temp + c)

    fun = bc.transform.StatefulFunction(func4).make_jaxpr((jnp.zeros(8), jnp.ones(8)))
    print(fun.get_states())
    print(fun.get_jaxpr())

  def test_StatefulFunction_2(self):
    st1 = bc.State(jnp.ones(10))

    def f1(x):
      st1.value = x + st1.value

    def f2(x):
      jaxpr = bc.transform.make_jaxpr(f1)(x)
      c = 1. + x
      return c

    def f3(x):
      jaxpr = bc.transform.make_jaxpr(f1)(x)
      c = 1.
      return c

    print()
    jaxpr = bc.transform.make_jaxpr(f1)(jnp.zeros(1))
    print(jaxpr)
    jaxpr = jax.make_jaxpr(f2)(jnp.zeros(1))
    print(jaxpr)
    jaxpr = jax.make_jaxpr(f3)(jnp.zeros(1))
    print(jaxpr)
    jaxpr, _ = bc.transform.make_jaxpr(f3)(jnp.zeros(1))
    print(jaxpr)
    self.assertTrue(jnp.allclose(jax.core.jaxpr_as_fun(jaxpr)(jnp.zeros(1), st1.value)[0],
                                 f3(jnp.zeros(1))))

  def test_compar_jax_make_jaxpr2(self):
    st1 = bc.State(jnp.ones(10))

    def fa(x):
      st1.value = x + st1.value

    def ffa(x):
      jaxpr, states = bc.transform.make_jaxpr(fa)(x)
      c = 1. + x
      return c

    jaxpr, states = bc.transform.make_jaxpr(ffa)(jnp.zeros(1))
    print()
    print(jaxpr)
    print(states)
    print(jax.core.jaxpr_as_fun(jaxpr)(jnp.zeros(1), st1.value))
    jaxpr = jax.make_jaxpr(ffa)(jnp.zeros(1))
    print(jaxpr)
    print(jax.core.jaxpr_as_fun(jaxpr)(jnp.zeros(1)))

  def test_compar_jax_make_jaxpr3(self):
    def fa(x):
      return 1.

    jaxpr, states = bc.transform.make_jaxpr(fa)(jnp.zeros(1))
    print()
    print(jaxpr)
    print(states)
    # print(jax.core.jaxpr_as_fun(jaxpr)(jnp.zeros(1)))
    jaxpr = jax.make_jaxpr(fa)(jnp.zeros(1))
    print(jaxpr)
    # print(jax.core.jaxpr_as_fun(jaxpr)(jnp.zeros(1)))


def test_return_states():
  import jax.numpy

  import brainstate as bc

  a = bc.State(jax.numpy.ones(3))

  @bc.transform.jit
  def f():
    return a

  with pytest.raises(ValueError):
    f()


