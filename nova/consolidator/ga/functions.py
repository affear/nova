import random
from oslo_config import cfg

tournament_opts = [
    cfg.FloatOpt(
        'p',
        default=1.0,
        help='The wheight p of the tournament selection'
    ),
    cfg.IntOpt(
        'k_perc',
        default=25,
        help='The percentage of the population on which apply the selection'
    )
]

CONF = cfg.CONF
cons_group = 'consolidator'
CONF.import_group(cons_group, 'nova.consolidator.base')
CONF.register_opts(tournament_opts, cons_group)

class SelectionAlgorithm(object):
	'''
		Base class for selection algorithms.
		The given population is expected to be ordered
		by fitness
	'''
	def __init__(self, population):
		super(SelectionAlgorithm, self).__init__()
		self.population = population

	def get_chromosome(self):
		raise NotImplementedError


class CrossoverFunction(object):
	'''
		Base class for crossover functions
	'''
	def __init__(self, father, mother):
		super(CrossoverFunction, self).__init__()
		self.father = father
		self.mother = mother

	def cross(self):
		raise NotImplementedError


class FitnessFunction(object):
	'''
		Base class for fitness functions
	'''
	def __init__(self, chromosome):
		super(FitnessFunction, self).__init__()
		self.chromosome = chromosome

	def get(self):
	 	raise NotImplementedError

##### implementations

class TournamentSelection(SelectionAlgorithm):
	P = CONF.consolidator.p
	K = CONF.consolidator.k_perc

	def __init__(self, population):
		super(TournamentSelection, self).__init__(population)
		pop_len = len(self.population)
		no_select = int((float(self.K) / 100) * pop_len)

		# choose k individuals randomly
		indexes = list(xrange(0, no_select))
		chosen = []
		for k in xrange(0, no_select):
			i = random.choice(indexes)
			chosen.append(i)
			indexes.remove(i)

		chosen.sort()

		# expect population to be already sorted by fitness
		p = self.P
		self.probs = [p * ((1 - p) ** i) for i in xrange(0, len(chosen))] # 0 ** 0 = 1
		self.pool_indexes = chosen

	def _weighted_choice(self, weights):
		'''
			:param:choices: list of weights
			:returns: chosen index of the list of weights
		'''
		total = sum(weights)
		r = random.uniform(0, total)
		upto = 0

		for i, w in enumerate(weights):
			if upto + w >= r:
				return i
			upto += w

		raise Exception('Choice out of scope!')

	def get_chromosome(self):
		i = self._weighted_choice(self.probs)
		chosen_index = self.pool_indexes[i]
		return self.population[chosen_index]


class RouletteSelection(TournamentSelection):
	# a 1-way tournament is equivalent to random selection
	K = float(100) / CONF.consolidator.population_size

class SinglePointCrossover(CrossoverFunction):
	def __init__(self, father, mother):
		super(SinglePointCrossover, self).__init__(father, mother)
		self.cut_point = random.randint(0, len(self.father))

	def cross(self):
		first_piece = self.father[:self.cut_point]
		second_piece = self.mother[self.cut_point:]
		first_piece.extend(second_piece)
		return first_piece

class RandomFitnessFunction(FitnessFunction):

	def get(self):
		return random.random()


metric_fitness_opts = [
    cfg.FloatOpt(
        'vcpu_weight',
        default=0.4,
        help='VCPUs wheight in metrics fitness function weighted mean'
    ),
    cfg.FloatOpt(
        'ram_weight',
        default=0.4,
        help='RAM wheight in metrics fitness function weighted mean'
    ),
    cfg.FloatOpt(
        'disk_weight',
        default=0.2,
        help='Disk wheight in metrics fitness function weighted mean'
    ),
]

CONF.register_opts(metric_fitness_opts, cons_group)

class MetricsFitnessFunction(FitnessFunction):
	VCPU_W = CONF.consolidator.vcpu_weight
	RAM_W = CONF.consolidator.ram_weight
	DISK_W = CONF.consolidator.disk_weight

	def get(self):
		l = len(self.chromosome.genes)
		vcpu_r = [g.vcpu_r for g in self.chromosome.genes.values()]
		memory_mb_r = [g.memory_mb_r for g in self.chromosome.genes.values()]
		local_gb_r = [g.local_gb_r for g in self.chromosome.genes.values()]

		# extract avgs
		vcpu_r = float(sum(vcpu_r)) / l
		memory_mb_r = float(sum(memory_mb_r)) / l
		local_gb_r = float(sum(local_gb_r)) / l

		# the more resources are utilized, the better it is
		return vcpu_r * self.VCPU_W + memory_mb_r * self.RAM_W + local_gb_r * self.DISK_W