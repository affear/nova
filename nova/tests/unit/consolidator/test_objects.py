"""
Unit Tests for nova.consolidator.objects
"""

import mock
from nova import context
from nova import test
from nova.consolidator import objects as cons_objects
from nova.tests.unit.api.openstack import fakes
from nova.tests.unit.objects import test_compute_node
from nova.objects import instance, compute_node

class ConsolidatorObjectsTestCase(test.TestCase):

	# mapping host_id -> number of instances
	architecture = {
		0: 1,
		1: 4,
		2: 0,
		3: 10,
		4: 7,
		5: 3,
		6: 0
	}

	def setUp(self):
		super(ConsolidatorObjectsTestCase, self).setUp()
		self.ctxt = context.get_admin_context()
		self.snapshot = cons_objects.Snapshot(self.ctxt)
		self.cns = self._get_compute_nodes()

	def _get_compute_nodes(self):
		hosts = []
		for k in self.architecture:
			host = test_compute_node.fake_compute_node.copy()
			host['id'] = k
			host_obj = compute_node.ComputeNode._from_db_object(self.ctxt, compute_node.ComputeNode(), host)
			hosts.append(host_obj)
		return [cons_objects._ComputeNodeWrapper(self.ctxt, h) for h in hosts]

	def _get_instances_by_host(self, host):
		id = str(host.id) + '{}'
		instances = []
		for i, cn in enumerate(self.cns):
			instance = fakes.stub_instance(host=cn, id=id.format(i))
			instances.append(instance)
		return instances

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