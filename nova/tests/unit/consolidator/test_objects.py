"""
Unit Tests for nova.consolidator.objects
"""


from nova import context
from nova import test
from nova.consolidator import objects as cons_objects
from nova.tests.api import fakes
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
		self.ctxt = context.get_admin_context()
		self.snapshot = cons_objects.Snapshot(self.ctxt)

	def _get_compute_nodes(self):
		hosts = []
		for h_id in self.architecture:
			host = test_compute_node.fake_compute_node.copy()
			host['id'] = h_id
			hosts.append(host)
		return [compute_node._from_db_object(self.ctxt, compute_node.ComputeNode(), h) for h in hosts]

	def _get_instances_by_host(self, host):
		return [fakes.stub_instance(host=host) for i in xrange(self.architecture[host.id])]

	def test_returned_compute_nodes_from_snapshot(self):
		self.stubs.Set(self.snapshot, '_get_compute_nodes', self._get_compute_nodes)
		self.assertItemsEqual(self._get_compute_nodes(), self.snapshot.nodes)