from oslo_log import log as logging
from nova.i18n import _LI
from oslo_config import cfg
from nova.consolidator.objects import Snapshot

cons_group = cfg.OptGroup(name='consolidator')
rnd_consolidator_opts = [
	cfg.IntOpt(
		'migration_percentage',
		default=1,
		help='The percentage of running instances to migrate at each step'
	),
]

CONF = cfg.CONF
CONF.register_group(cons_group)
CONF.register_opts(rnd_consolidator_opts, cons_group)

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
		LOG.debug(str(snapshot))
		nodes = snapshot.nodes
		no_nodes = len(nodes)
		migration_percentage = float(CONF.consolidator.migration_percentage) / 100
		assert migration_percentage > 0 and migration_percentage < 100
		no_inst = len(snapshot.instances_migrable)
		no_inst_migrate = int(no_inst * migration_percentage)

		if no_inst == 0:
			LOG.info(_LI('No running instance found. Cannot migrate.'))
			return []

		if no_inst_migrate == 0:
			LOG.info(_LI('Too few instances. Cannot migrate.'))
			return []

		if no_nodes == 0:
			LOG.info(_LI('No compute node in current snapshot'))
			return []

		if no_nodes == 1:
			LOG.info(_LI('Only one compute node in current snapshot. Cannot migrate.'))
			return []

		LOG.debug('Migrating {} instances...'.format(no_inst_migrate))

		def choose_host(nodes):
			no_nodes = len(nodes)

			from_host = random.choice(nodes)
			instances = from_host.instances_migrable
			explored_nodes = 1

			while len(instances) == 0 and explored_nodes < no_nodes:
				explored_nodes += 1
				nodes.remove(from_host)
				from_host = random.choice(nodes)
				instances = from_host.instances_migrable

			if explored_nodes == no_nodes:
				LOG.info(_LI('No running instance found. Cannot migrate.'))
				return None
			return from_host

		migs = []
		while no_inst_migrate > 0:
			nodes_cpy = list(nodes)

			from_host = choose_host(nodes_cpy)

			inst_on_host = from_host.instances_migrable
			no_inst_on_host = len(inst_on_host)

			top_bound = min(no_inst_on_host, no_inst_migrate)
			n = random.randint(1, top_bound)
			no_inst_migrate -= n

			instances = random.sample(inst_on_host, n)
			nodes_cpy.remove(from_host)
			to_host = random.choice(nodes_cpy)
			for i in instances:
				migs.append(self.Migration(i, to_host))

		return migs
