#
# Copyright (c) 2015 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from nova import test
from nova.virt import driver
from nova.virt import fake


class FakeDriverTest(test.NoDBTestCase):

    def test_public_api_signatures(self):
        baseinst = driver.ComputeDriver(None)
        inst = fake.FakeDriver(fake.FakeVirtAPI(), True)
        self.assertPublicAPISignatures(baseinst, inst)

    def test_multiplier_fake_driver(self):
        MULT_OVER = 3
        MULT_UNDER = 0.5
        attrs = ['vcpus', 'memory_mb', 'local_gb']

        fake.MStandardFakeDriver._MULT = MULT_OVER
        inst = fake.MStandardFakeDriver(fake.FakeVirtAPI(), True)

        stds = {a: getattr(fake.StandardFakeDriver, a) for a in attrs}
        for s in stds:
          self.assertEqual(stds[s] * MULT_OVER, getattr(inst, s))

        fake.MStandardFakeDriver._MULT = MULT_OVER
        inst = fake.MStandardFakeDriver(fake.FakeVirtAPI(), True)

        stds = {a: getattr(fake.StandardFakeDriver, a) for a in attrs}
        for s in stds:
          self.assertEqual(stds[s] * MULT_OVER, getattr(inst, s))

        fake.MStandardFakeDriver._MULT = MULT_UNDER
        inst = fake.MStandardFakeDriver(fake.FakeVirtAPI(), True)

        stds = {a: getattr(fake.StandardFakeDriver, a) for a in attrs}
        for s in stds:
          self.assertEqual(stds[s] * MULT_UNDER, getattr(inst, s))
