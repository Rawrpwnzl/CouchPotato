from app.lib.provider.yarr.sources.nzbs import nzbs
from app.lib.provider.yarr.sources.tpb import tpb
from app.lib.qualities import Qualities
import logging
import time

log = logging.getLogger(__name__)

class Searcher():

    sources = []

    def __init__(self, config, debug):

        self.config = config
        self.debug = debug

        #config nzbs
        s = nzbs(config)
        self.sources.append(s)

        t = tpb(config)
        self.sources.append(t)


    def find(self, movie, queue):
        ''' Find movie by name '''
        log.debug('Searching for movie: %s', movie.name)

        qualities = Qualities()

        wait = 1 if self.debug else 5

        for source in self.sources:

            results = []

            # find by main name
            type = queue.qualityType
            results.extend(source.find(movie, type, type))
            time.sleep(wait)

            # Search for alternative naming
            for alt in qualities.getAlternatives(type):
                results.extend(source.find(movie, alt, type))
                time.sleep(wait)

            if results:
                return results

        return {}

    def findById(self, id):
        ''' Find movie by TheMovieDB ID '''

        for source in self.sources:
            result = source.findById(id)
            if result:
                return result

        return []



    def findByImdbId(self, id):
        ''' Find movie by IMDB ID '''

        for source in self.sources:
            result = source.findByImdbId(id)
            if result:
                return result

        return []
