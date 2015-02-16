"""
Unit Tests for nova.consolidator.base
"""

import contextlib

import mock
from oslo_config import cfg
from nova import context
from nova import test
from nova.consolidator import base
from nova.consolidator import objects as cons_objects
from nova.tests.unit import fake_instance
from nova.tests.unit.consolidator import base as test_base

CONF = cfg.CONF

class BaseConsolidatorTestCase(test.TestCase):

	def setUp(self):
		super(BaseConsolidatorTestCase, self).setUp()
		self.context = context.get_admin_context()
		self.consolidator = base.BaseConsolidator()
		self.Migration = self.consolidator.Migration
		
		self.host_names = ['hostA', 'hostB', 'hostC', 'hostD']
		self.fake_instances = [
			self._create_fake_instance(0, self.host_names[0]),
			self._create_fake_instance(1, self.host_names[0]),
			self._create_fake_instance(2, self.host_names[1]),
			self._create_fake_instance(3, self.host_names[1]),
			self._create_fake_instance(4, self.host_names[1]),
			self._create_fake_instance(5, self.host_names[2]),
			self._create_fake_instance(6, self.host_names[3]),
		]
		self.fake_migrations_ok = [
			self.Migration(self.fake_instances[0], self.host_names[1]),
			self.Migration(self.fake_instances[2], self.host_names[2]),
			self.Migration(self.fake_instances[3], self.host_names[0]),
			self.Migration(self.fake_instances[5], self.host_names[0]),
		]

		self.fake_migrations_ko = [
			self.Migration(self.fake_instances[0], self.host_names[1]), # expected to disappear
			self.Migration(self.fake_instances[2], self.host_names[2]), 
			self.Migration(self.fake_instances[3], self.host_names[0]), # expected to disappear
			self.Migration(self.fake_instances[5], self.host_names[0]),
			self.Migration(self.fake_instances[0], self.host_names[2]),
			self.Migration(self.fake_instances[3], self.host_names[3]),
			self.Migration(self.fake_instances[1], self.host_names[3]), # expected to disappear
			self.Migration(self.fake_instances[1], self.host_names[2])
		]

	def _create_fake_instance(self, id, host_name):
		instance_attr = {'host': host_name, 'id': id}
		return fake_instance.fake_instance_obj(self.context, **instance_attr)

	def test_consolidate_with_closed_migrations(self):
		self.consolidator.get_migrations = mock.Mock(return_value=self.fake_migrations_ok)
		res = self.consolidator.consolidate(self.context)
		self.assertSequenceEqual(res, self.fake_migrations_ok)

	def test_consolidate_with_not_closed_migrations(self):
		self.consolidator.get_migrations = mock.Mock(return_value=self.fake_migrations_ko)
		expected = list(self.fake_migrations_ko) #copy
		del expected[0]
		del expected[1]
		del expected[4]
		real = self.consolidator.consolidate(self.context)
		self.assertItemsEqual(expected, real)

class RandomConsolidatorTestCase(test_base.TestCaseWithSnapshot):

	def setUp(self):
		super(RandomConsolidatorTestCase, self).setUp()
		self.consolidator = base.RandomConsolidator()
		self.snapshot = self._get_snapshot(no_nodes=len(self.cns))

	def test_random_returns_one_migration(self):
		migs = self.consolidator.get_migrations(self.snapshot)
		self.assertTrue(len(migs) == 1)

	def test_consistent_migration(self):
		m = self.consolidator.get_migrations(self.snapshot)[0]
		self.assertTrue(m.instance.host != m.host.host)

	def test_no_nodes(self):
		snapshot = self._get_snapshot(no_nodes=0)
		migs = self.consolidator.get_migrations(snapshot)
		self.assertTrue(len(migs) == 0)

	def test_one_node(self):
		snapshot = self._get_snapshot(no_nodes=1)
		migs = self.consolidator.get_migrations(snapshot)
		self.assertTrue(len(migs) == 0)

	def test_no_instance(self):
		old_arch = self.architecture.copy()
		self.architecture = {
			0: 0,
			1: 0,
			2: 0,
			3: 0,
			4: 0,
			5: 0,
			6: 0
		}
		snapshot = self._get_snapshot(no_nodes=len(self.cns))
		migs = self.consolidator.get_migrations(snapshot)
		self.assertTrue(len(migs) == 0)
		# reset arch
		self.architecture = old_arch