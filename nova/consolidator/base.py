from nova.openstack.common import log as logging
from oslo_config import cfg

CONF = cfg.CONF

LOG = logging.getLogger(__name__)

class BaseConsolidator(object):

	def __init__(self):
		super(BaseConsolidator, self).__init__()

	class Migration(object):
		def __init__(self, instance, host_name):
			self.instance = instance
			self.host_name = host_name

		def __repr__(self):
			return '{} --> {}'.format(self.instance.id, self.host_name)

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

	def consolidate(self):
		migs = self.get_migrations()
		return self._transitive_closure(migs)

	def get_migrations(self):
		'''
			Base method to be overridden to obtain consolidation.
			:returns: a list of Migration
		'''
		return []
