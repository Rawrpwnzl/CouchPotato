from app import latinToAscii
from app.config.cplog import CPLog
from app.config.db import RenameHistory, Session as Db
from app.controllers.movie import MovieController
from app.lib.cron.base import cronBase
from app.lib.library import Library
from app.lib.provider.rss import rss

from xmg import xmg
import cherrypy
import os
import re
import shutil
import time
import traceback


log = CPLog(__name__)

class MovieRSSCron(cronBase, Library, rss):

    ''' Cronjob for getting blu-ray.com releases '''

    lastChecked = 0
    intervalSec = 86400
    config = {}
    MovieRSSUrl = "http://www.blu-ray.com/rss/newreleasesfeed.xml"

    def conf(self, option):
        return
#        return self.config.get('MovieRSS', option)

    def run(self):
        log.info('Movie RSS thread is running.')

        wait = 0.1 if self.debug else 5

        time.sleep(10)
        while True and not self.abort:
            now = time.time()
            if (self.lastChecked + self.intervalSec) < now:
                try:
                    self.running = True
                    self.lastChecked = now
                    self.doRSSCheck()
                    self.running = False
                except Exception as exc:
                    log.error("!!Uncought exception in movie RSS thread.")
                    log.error(traceback.format_exc())
            time.sleep(wait)

        log.info('Movie RSS has shutdown.')

    def isDisabled(self):

        #if (self.conf('enabled'):
            
            return False
        #else:

        #    return True

    def doRSSCheck(self):
        '''
        Go find movies and add them!
        '''

        log.info('Starting Movies RSS check')

        if self.isDisabled():
            log.info('Movie RSS has been disabled')
            return

        if not self.isAvailable(self.MovieRSSUrl):
            log.info('Movie RSS is not available')
            return

        RSSData = self.urlopen(self.MovieRSSUrl)
        RSSItems = self.getItems(RSSData)
        
        RSSMovies = []
        RSSMovie = {'name': 'test', 'year' : '2009'}
        
        MyMovieController = MovieController()
                        
        for RSSItem in RSSItems:
            RSSMovie['name'] = self.gettextelement(RSSItem, "title").lower().split("blu-ray")[0].strip("(").rstrip() #strip Blu-ray and spaces
            RSSMovie['year'] = self.gettextelement(RSSItem, "description").split("|")[1].strip("(").strip() #find movie year in description
            
            if not RSSMovie['name'].find("/") == -1: # make sure it is not a double movie release
                continue 
                
            if int(RSSMovie['year']) < 2009: #do year filtering
                continue  
                
            for test in RSSMovies:
                if test.values() == RSSMovie.values(): # make sure we did not already include it...
                    break
            else:
                log.info('Release found: %s.' % RSSMovie)
                RSSMovies.append(RSSMovie.copy())
                
        if not RSSMovies:
            log.info('No movies found.')
            return

        log.info("Applying IMDB filter to found movies...")

        for RSSMovie in RSSMovies:
            if self.abort: #this loop takes a while, stop when the program needs to close
                return

            time.sleep(5) # give the system some slack
            
            log.debug('Searching for "%s".' % RSSMovie)
            try:
                result = cherrypy.config['searchers']['movie'].find(RSSMovie['name'] + ' ' + RSSMovie['year'], limit = 1)
            except:
                pass

            if not result:
                log.info('Movie not found: "%s".' % RSSMovie )
                continue

            try:
                imdbmovie = cherrypy.config['searchers']['movie'].sources[1].findByImdbId(result.imdb, True)
            except:
                pass

            if not ( imdbmovie.get('kind') == 'movie' ):
                log.info('This is not a movie: "%s".' % RSSMovie )
                continue
            
            if not imdbmovie.get('year'):
                log.info('IMDB has trouble with the year, skipping: "%s".' % RSSMovie )
                continue
            
            if not imdbmovie.get('rating'):
                log.info('Rating is unknown for this movie: "%s".' % RSSMovie )
                continue
                        
            if float(imdbmovie.get('rating')) < 5.5:
                log.info('Rating is too low for this movie: "%s".' % RSSMovie )
                continue
            
            log.info('Adding movie to queue: %s.' % imdbmovie.get('title') + ' (' + str(imdbmovie.get('year')) + ') Rating: ' + str(imdbmovie.get('rating')))
            try:
                MyMovieController._addMovie(result, 8)
            except:
                log.info('MovieController unable to add this movie: "%s".' % RSSMovie )

def startMovieRSSCron(config, searcher, debug):
    cron = MovieRSSCron()
    cron.config = config
    cron.searcher = searcher
    cron.debug = debug
    cron.start()

    return cron
