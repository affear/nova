from oslo_config import cfg
from nova.openstack.common import log as logging
import oslo_messaging as messaging
from nova.objects import base as objects_base
from nova import rpc

rpcapi_opts = [
	cfg.StrOpt(
		'consolidator_topic',
		default='consolidator',
		help='The topic compute nodes listen on'
	),
]

CONF = cfg.CONF
CONF.register_opts(rpcapi_opts)

<<<<<<< HEAD
rpcapi_cap_opt = cfg.StrOpt(
	'consolidator',
	help='Set a version cap for messages sent to consolidator services. If you '
				'plan to do a live upgrade from havana to icehouse, you should '
				'set this option to "icehouse-compat" before beginning the live '
				'upgrade procedure.'
)
CONF.register_opt(rpcapi_cap_opt, 'upgrade_levels')

=======
>>>>>>> Full structure for rpc service.
LOG = logging.getLogger(__name__)

class ConsolidatorAPI(object):

	VERSION_ALIASES = {
		'icehouse': '3.23',
		'juno': '3.35',
	}

	def __init__(self):
		super(ConsolidatorAPI, self).__init__()
		target = messaging.Target(topic=CONF.consolidator_topic, version='3.0')
		version_cap = self.VERSION_ALIASES.get(CONF.upgrade_levels.consolidator, CONF.upgrade_levels.consolidator)
		serializer = objects_base.NovaObjectSerializer()
		self.client = self.get_client(target, version_cap, serializer)

	def get_client(self, target, version_cap, serializer):
		return rpc.get_client(
			target,
			version_cap=version_cap,
			serializer=serializer
		)

	def log_sth(self, ctxt):
		cctxt = self.client.prepare()
		cctxt.cast(ctxt, 'log_sth')