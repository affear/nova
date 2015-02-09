class BaseConsolidator(object):

	class Migration(object):
		def __init__(self, instance_id, host_id):
			self.instance_id = instance_id
			self.host_id = host_id

	def _consolidate(self):
		# do things
		migs = do_consolidate()
		# apply transitive closure to migs
		return migs
		

	def do_consolidate(self):
		'''
			Base method to be overridden to obtain consolidation.
			:returns: a list of Migration
		'''
		return []