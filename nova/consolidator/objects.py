'''
	This module contains wrappers and abstractions 
	for nova objects, with the aim to give to the developer
	who implements a consolidation algorithm a system snapshot
	easy to access:

	>>> s = Snapshot(ctxt)
	>>> nodes = snapshot.nodes # all compute nodes
	>>> node = nodes[0] # the first node
	>>> instance = node.instances[0] # all instances on that node (list)
	>>> node.vcpu
	>>> node.id
	>>> # node has all attributes as nova.objects.compute_node.ComputeNode has,
	>>> # as well as instance has all attributes as nova.objects.instance.Instance has.
	>>> ...

	The Snapshot is thought to be renewed at each consolidation cycle, so:
		- Any Snapshot attribute is lazily obtained on the first call.
		- Subsequent call won't refresh objects state.
		- The Snapshot is entirely cached.
'''
from nova.objects import compute_node, instance

class _ComputeNodeWrapper(object):
	'''
		Wrapper for nova.objects.compute_node.ComputeNode class.
	'''
	def __init__(self, ctxt, real_compute_node_object):
		super(_ComputeNodeWrapper, self).__init__()
		self.cn = real_compute_node_object
		self.ctxt = ctxt
		self._instances = None

	def __getattr__(self, name):
		# something like a method missing
		# any call to wrapper.attr is redirected to wrapper.cn.attr
		# only if wrapper has no attribute `attr`
		try:
			return super(_ComputeNodeWrapper, self).__getattr__(name)
		except AttributeError:
			return getattr(self.cn, name)

	@property
	def instances(self):
		if self._instances is None:
			self._instances = self._get_instances()
		return self._instances

	def _get_instances(self):
		return instance.InstanceList.get_by_host(self.ctxt, self.cn.host).objects


class Snapshot(object):
	'''
		Abstraction for a system snapshot.
	'''
	@property
	def nodes(self):
		if self._cns is None:
			real_cns = self._get_compute_nodes()
			self._cns = [_ComputeNodeWrapper(self.ctxt, cn) for cn in real_cns]
		return self._cns

	def __init__(self, ctxt):
		super(Snapshot, self).__init__()
		self.ctxt = ctxt
		self._cns = None

	def __repr__(self):
		res = 'Snapshot object (host_name -> no_instances):'
		for node in self.nodes:
			row = '{} -> {}'
			'\n'.join([res, row.format(node.host, len(node.instances))])
		return res

	def _get_compute_nodes(self):
		return compute_node.ComputeNodeList.get_all(self.ctxt).objects