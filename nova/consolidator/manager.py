from oslo_config import cfg
from oslo_utils import importutils
import oslo_messaging as messaging
from nova.openstack.common import log as logging
from nova import manager
from nova.openstack.common import periodic_task
from nova.compute import api as compute_api

consolidator_opts = [
	cfg.StrOpt(
		'consolidator_class',
		default='nova.consolidator.base.BaseConsolidator',
		help='Full class name for consolidation algorithm'
	),
]

interval_opts = [
	cfg.IntOpt(
		'consolidation_interval',
		default=10,
		help='Number of seconds between two consolidation cycles'
	),
	cfg.IntOpt(
		'apply_migrate_interval',
		default=20,
		help='Number of seconds among application of live migrations'
	)
]

CONF = cfg.CONF
CONF.register_opts(consolidator_opts)
CONF.register_opts(interval_opts)

LOG = logging.getLogger(__name__)

# REMEMBER:
# from nova.i18n import _LE
# from nova.i18n import _LI
# from nova.i18n import _LW
#
# LOG.warning(_LW('warning message'))
# LOG.info(_LI('info message'))
# LOG.error(_LE('error message'))

class ConsolidatorManager(manager.Manager):

	target = messaging.Target(version='3.38')

	def __init__(self, *args, **kwargs):
		self.migrations = []
		self.compute_api = compute_api.HostAPI()
		self.consolidator = importutils.import_class(CONF.consolidator_class)()
		super(ConsolidatorManager, self).__init__(service_name="consolidator", *args, **kwargs)

	@periodic_task.periodic_task(spacing=CONF.consolidation_interval)
	def consolidate(self, ctxt):
		#self.notifier.audit(ctxt, 'consolidator.consolidation.start', '')

		LOG.debug('Consolidation cycle started')
		migrations = self.consolidator.consolidate()
		for m in migrations:
			self._do_live_migrate(m)
		LOG.debug('Consolidation cycle ended')

		#self.notifier.audit(ctxt, 'consolidator.consolidation.end', '')

	def _do_live_migrate(self, migration):
		# self.compute_api.live_migrate(context, instance, block_migration, disk_over_commit, host_name)
		# From python-novaclient:
		#
		# def live_migrate(self, host=None, block_migration=False, disk_over_commit=False):
  	#   ....
		# I think
		# self.compute_api.live_migrate(ctxt, m.instance, False, False, m.host_name)
		LOG.debug('Applying migration: %s', str(migration))
