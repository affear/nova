from oslo_config import cfg
from oslo_utils import importutils
import oslo_messaging as messaging
from nova.openstack.common import log as logging
from nova import manager
from nova.compute import rpcapi as compute_rpcapi
from nova.openstack.common import periodic_task

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
		default=60,
		help='Number of seconds between two consolidation cycles'
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
# LOG.warning(_LI('warning message'))
# LOG.info(_LI('info message'))
# LOG.error(_LI('error message'))

class ConsolidatorManager(manager.Manager):

	target = messaging.Target(version='3.38')

	def __init__(self, *args, **kwargs):
		self.compute_rpcapi = compute_rpcapi.ComputeAPI()
		self.consolidator = importutils.import_class(CONF.consolidator_class)()
		super(ConsolidatorManager, self).__init__(service_name="consolidator", *args, **kwargs)

	def log_sth(self, ctxt):
		import random
		strings = ['foo', 'bar', 'baz', 'boo', 'wof']

		LOG.debug('Consolidator says: ' + random.choice(strings) + '!')

	@periodic_task.periodic_task(spacing=CONF.consolidation_interval)
	def consolidate(self, ctxt):
		#self.notifier.audit(ctxt, 'consolidator.consolidation.start', '')
		LOG.debug('Consolidation cycle started')
		self.consolidator.consolidate()
		#self.notifier.audit(ctxt, 'consolidator.consolidation.end', '')
