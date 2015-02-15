from nova.openstack.common import log as logging
from oslo_config import cfg
from nova.consolidator.objects import Snapshot

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class BaseConsolidator(object):

	class Migration(object):
		'''
			Simple abstraction for a migration
		'''
		def __init__(self, instance, host):
			super(BaseConsolidator.Migration, self).__init__()
			self.instance = instance
			self.host = host

		def __repr__(self):
			return '{} --> {}'.format(self.instance.id, self.host.host or self.host.id)

	def __init__(self):
		super(BaseConsolidator, self).__init__()

	def _transitive_closure(self, migs):
		closed_migs = []
		migs_by_instance_id = [m.instance.id for m in migs]
		rev_migs = list(reversed(migs))
		rev_migs_by_instance_id = list(reversed(migs_by_instance_id))
		unique_instance_ids = list(set(migs_by_instance_id))

		for id in unique_instance_ids:
			last_matching_mig_index = rev_migs_by_instance_id.index(id)
			closed_migs.append(rev_migs[last_matching_mig_index])

		return closed_migs

	def consolidate(self, ctxt):
		snapshot = Snapshot(ctxt)
		migs = self.get_migrations(snapshot)
		return self._transitive_closure(migs)

	def get_migrations(self, snapshot):
		'''
			Base method to be overridden to obtain consolidation.

			:param:snapshot: a nova.consolidator.objects.Snapshot object
			:returns: a list of Migration
		'''
		return []

import random
class RandomConsolidator(BaseConsolidator):
	'''
		Useless consolidator. Provided only as example.
		Picks a random instance and migrates it to another random host
	'''

	def get_migrations(self, snapshot):
		nodes = snapshot.nodes
		from_host = random.choice(nodes)
		instances = from_host.instances

		while len(instances) == 0:
			from_host = random.choice(nodes)
			instances = from_host.instances

		instance = random.choice(instances)
		nodes.remove(from_host)
		to_host = random.choice(nodes)

		migration = self.Migration(instance, to_host)
		return [migration]
