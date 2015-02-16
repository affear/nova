import mock
from nova import context
from nova import test
from nova.consolidator import objects as cons_objects
from nova.tests.unit.api.openstack import fakes
from nova.tests.unit.objects import test_compute_node
from nova.objects import instance, compute_node

class TestCaseWithSnapshot(test.TestCase):

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
		super(TestCaseWithSnapshot, self).setUp()
		self.ctxt = context.get_admin_context()
		self.snapshot = cons_objects.Snapshot(self.ctxt)
		self.cns = self._get_compute_nodes()

	def _get_snapshot(self, no_nodes=1):
		# mocking snapshot
		snapshot = cons_objects.Snapshot(self.ctxt)
		nodes = self.cns[:no_nodes]
		snapshot._get_compute_nodes = mock.Mock(return_value=nodes)
		for node in snapshot.nodes:
			instances = self._get_instances_by_host(node.cn)
			node._get_instances = mock.Mock(return_value=instances)
		return snapshot

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
		for i in xrange(self.architecture[host.id]):
			inst = fakes.stub_instance(host=host, id=id.format(i))
			inst_obj = instance.Instance._from_db_object(self.ctxt, instance.Instance(), inst)
			instances.append(inst_obj)
		return instances