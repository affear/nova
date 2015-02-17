"""
Unit Tests for nova.consolidator.objects
"""

import mock
from nova.tests.unit.consolidator import base
from nova.compute import vm_states, power_state

class ConsolidatorObjectsTestCase(base.TestCaseWithSnapshot):

	def test_wrapper_method_missing(self):
		cn = self.cns[0] # wrapped
		self.assertRaises(AttributeError, lambda name: getattr(cn, name), 'not_existent_attribute')
		self.assertEquals(cn.id, cn.cn.id)
		self.assertEquals(cn.vcpus, cn.cn.vcpus)
		self.assertEquals(cn.memory_mb, cn.cn.memory_mb)
		self.assertEquals(cn.local_gb, cn.cn.local_gb)
		val = 'doesnt_matter'
		cn._get_instances = mock.Mock(return_value=val)
		self.assertEquals(cn.instances, val)

	def test_returned_compute_nodes_from_snapshot(self):
		self.stubs.Set(self.snapshot, '_get_compute_nodes', self._get_compute_nodes)
		cfr_id_expected = [cn.id for cn in self.cns]
		cfr_id_real = [cn.id for cn in self.snapshot.nodes]
		self.assertItemsEqual(cfr_id_expected, cfr_id_real)

	def test_returned_instances_from_cn(self):
		for node in self.cns:
			instances = self._get_instances_by_host(node.cn)
			self.stubs.Set(node, '_get_instances', lambda: instances)
			self.assertItemsEqual(node.instances, instances)

	def test_active_instances_are_active(self):
		for node in self.cns:
			instances = self._get_instances_by_host(node.cn)
			self.stubs.Set(node, '_get_instances', lambda: instances)
			ai = node.instances_active
			for i in ai:
				self.assertTrue(i.vm_state == vm_states.ACTIVE)

	def test_running_instances_are_running(self):
		for node in self.cns:
			instances = self._get_instances_by_host(node.cn)
			self.stubs.Set(node, '_get_instances', lambda: instances)
			ai = node.instances_running
			for i in ai:
				self.assertTrue(i.power_state == power_state.RUNNING)

	def test_snapshot_instances(self):
		instances = []
		for node in self.cns:
			instances.extend(self._get_instances_by_host(node.cn))

		self.stubs.Set(self.snapshot, '_get_instances', lambda: instances)
		self.assertItemsEqual(instances, self.snapshot.instances)