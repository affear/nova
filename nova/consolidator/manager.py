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
		# TODO be threadsafe
		self.migrations = self.consolidator.consolidate()
		LOG.debug('Consolidation cycle ended')

		#self.notifier.audit(ctxt, 'consolidator.consolidation.end', '')

	@periodic_task.periodic_task(spacing=CONF.apply_migrate_interval)
	def _apply_migrations(self, ctxt):
		if len(self.migrations) == 0:
			LOG.debug('No migrations to apply')

		for m in self.migrations:
			# self.compute_api.live_migrate(context, instance, block_migration, disk_over_commit, host_name)
			# I think
			# self.compute_api.live_migrate(ctxt, m.instance, True, True, m.host.hostname)
			LOG.debug('Applying migration: %s', str(m))