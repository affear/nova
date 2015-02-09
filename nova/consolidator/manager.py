from oslo_config import cfg
import oslo_messaging as messaging
from nova.openstack.common import log as logging
from nova import manager
from nova.compute import rpcapi as compute_rpcapi
from nova.openstack.common import periodic_task

consolidator_opts = [
	cfg.IntOpt(
		'sample_opt',
		default=0,
		help='A sample option'
	),
]

CONF = cfg.CONF
CONF.register_opts(consolidator_opts)

LOG = logging.getLogger(__name__)

class ConsolidatorManager(manager.Manager):

	target = messaging.Target(version='3.38')

	def __init__(self, *args, **kwargs):
		self.compute_rpcapi = compute_rpcapi.ComputeAPI()
		super(ConsolidatorManager, self).__init__(service_name="consolidator", *args, **kwargs)

	def log_sth(self, ctxt):
		import random
		strings = ['foo', 'bar', 'baz', 'boo', 'wof']

		LOG.audit('Consolidator says: ' + random.choice(strings) + '!')
