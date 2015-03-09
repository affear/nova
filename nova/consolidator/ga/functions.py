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

  def get_chromosome(self, population, fitness_function):
    raise NotImplementedError


class CrossoverFunction(object):
  '''
    Base class for crossover functions
  '''
  HEALTHY = 'ok'
  UNHEALTHY = 'ko'
  NOT_APPLIED = 'na'

  def cross(self, father, mother):
    raise NotImplementedError


class FitnessFunction(object):
  '''
    Base class for fitness functions
  '''

  def get(self, chromosome):
    raise NotImplementedError

##### implementations

class TournamentSelection(SelectionAlgorithm):
  P = CONF.consolidator.p
  K = CONF.consolidator.k_perc
  POP_SIZE = CONF.consolidator.population_size
  _NO_SELECT = int((float(K) / 100) * POP_SIZE)

  def __init__(self):
    super(TournamentSelection, self).__init__()
    self._probs = None

  def _get_probs(self):
    if self._probs is None:
      return [self.P * ((1 - self.P) ** i) for i in xrange(0, self._NO_SELECT)] # 0 ** 0 = 1
    return self._probs  

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

  def get_chromosome(self, population, fitness_function):
    # choose k individuals randomly
    indexes = list(xrange(0, len(population)))
    chosen = []
    for k in xrange(0, self._NO_SELECT):
      i = random.choice(indexes)
      chosen.append(population[i])
      indexes.remove(i)

    chosen.sort(key=lambda ch: fitness_function(ch))

    i = self._weighted_choice(self._get_probs())
    return chosen[i]


class RouletteSelection(TournamentSelection):
  # a 1-way tournament is equivalent to random selection
  _NO_SELECT = 1

class SinglePointCrossover(CrossoverFunction):

  def cross(self, father, mother):
    cut_point = random.randint(0, len(father))
    first_piece = father[:cut_point]
    second_piece = mother[cut_point:]
    first_piece.extend(second_piece)
    return first_piece

class RandomFitnessFunction(FitnessFunction):

  def get(self, chromosome):
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
  )
]

CONF.register_opts(metric_fitness_opts, cons_group)
from nova.consolidator.ga import k

class MetricsFitnessFunction(FitnessFunction):
  VCPU_W = CONF.consolidator.vcpu_weight
  RAM_W = CONF.consolidator.ram_weight
  DISK_W = CONF.consolidator.disk_weight

  def get(self, ratios):
    # filter genes:
    # remove the empty ones
    ratios = filter(lambda m: k.get_vcpus(m) > 0, ratios)
    l = len(ratios)
    avgs = [float(r) / l for r in [sum(m) for m in zip(*ratios)]]

    # the more resources are utilized, the better it is
    return k.get_vcpus(avgs) * self.VCPU_W + \
      k.get_ram(avgs) * self.RAM_W + \
      k.get_disk(avgs) * self.DISK_W