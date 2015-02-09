from nova.openstack.common import log as logging
from oslo_config import cfg

CONF = cfg.CONF
CONF.register_opts(interval_opts)

LOG = logging.getLogger(__name__)

class BaseConsolidator(object):

	def __init__(self):
		super(BaseConsolidator, self).__init__()

	class Migration(object):
		def __init__(self, instance_id, host_id):
			self.instance_id = instance_id
			self.host_id = host_id

		def __repr__(self):
			return '%d --> %d' % (self.instance_id, self.host_id)

	def _transitive_closure(self, migs):
		# transitive closure
		return migs

	def consolidate(self):
		migs = self.get_migrations()
		return self._transitive_closure(migs)

	def get_migrations(self):
		'''
			Base method to be overridden to obtain consolidation.
			:returns: a list of Migration
		'''
		return []
