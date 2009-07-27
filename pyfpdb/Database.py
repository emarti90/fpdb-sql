#!/usr/bin/env python
"""Database.py

Create and manage the database objects.
"""
#    Copyright 2008, Ray E. Barker
#    
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#    
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#    
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

########################################################################

# postmaster -D /var/lib/pgsql/data

#    Standard Library modules
import sys
import traceback
from datetime import datetime, date, time, timedelta
from time import time, strftime
import string

#    pyGTK modules

#    FreePokerTools modules
import fpdb_db
import fpdb_simple
import Configuration
import SQL
import Card

class Database:

    MYSQL_INNODB = 2
    PGSQL = 3
    SQLITE = 4

    def __init__(self, c, db_name = None, game = None, sql = None): # db_name and game not used any more
        print "\ncreating Database instance, sql =", sql
        self.fdb = fpdb_db.fpdb_db()   # sets self.fdb.db self.fdb.cursor and self.fdb.sql
        self.fdb.do_connect(c)
        self.connection = self.fdb.db

        db_params = c.get_db_parameters()
        self.import_options = c.get_import_parameters()
        self.type = db_params['db-type']
        self.backend = db_params['db-backend']
        self.db_server = db_params['db-server']
        
        if self.backend == self.PGSQL:
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_READ_COMMITTED, ISOLATION_LEVEL_SERIALIZABLE
            #ISOLATION_LEVEL_AUTOCOMMIT     = 0
            #ISOLATION_LEVEL_READ_COMMITTED = 1 
            #ISOLATION_LEVEL_SERIALIZABLE   = 2

        # where possible avoid creating new SQL instance by using the global one passed in
        if sql == None:
            self.sql = SQL.Sql(type = self.type, db_server = db_params['db-server'])
        else:
            self.sql = sql

        # config while trying out new hudcache mechanism
        self.use_date_in_hudcache = True

                                   # To add to config:
        self.hud_session_gap = 30  # Gap (minutes) between hands that indicates a change of session
                                   # (hands every 2 mins for 1 hour = one session, if followed
                                   # by a 40 minute gap and then more hands on same table that is
                                   # a new session)
        self.hud_style = 'T'       # A=All-time 
                                   # S=Session
                                   # T=timed (last n days)
                                   # Future values may also include: 
                                   #                                 H=Hands (last n hands)
        self.hud_hands = 2000      # Max number of hands from each player to use for hud stats
        self.hud_days  = 30        # Max number of days from each player to use for hud stats

        self.hud_hero_style = 'T'  # Duplicate set of vars just for hero
        self.hud_hero_hands = 2000
        self.hud_hero_days  = 30

        self.cursor = self.fdb.cursor

        if self.fdb.wrongDbVersion == False:
            # self.hand_1day_ago used to fetch stats for current session (i.e. if hud_style = 'S')
            self.hand_1day_ago = 0
            self.cursor.execute(self.sql.query['get_hand_1day_ago'])
            row = self.cursor.fetchone()
            if row and row[0]:
                self.hand_1day_ago = row[0]
            #print "hand 1day ago =", self.hand_1day_ago

            # self.date_ndays_ago used if hud_style = 'T'
            d = timedelta(days=self.hud_days)
            now = datetime.utcnow() - d
            self.date_ndays_ago = "d%02d%02d%02d" % (now.year-2000, now.month, now.day)

            # self.hand_nhands_ago is used for fetching stats for last n hands (hud_style = 'H')
            # This option not used yet
            self.hand_nhands_ago = 0
            # should use aggregated version of query if appropriate
            self.cursor.execute(self.sql.query['get_hand_nhands_ago'], (self.hud_hands,self.hud_hands))
            row = self.cursor.fetchone()
            if row and row[0]:
                self.hand_nhands_ago = row[0]
            print "hand n hands ago =", self.hand_nhands_ago

            #self.cursor.execute(self.sql.query['get_table_name'], (hand_id, ))
            #row = self.cursor.fetchone()
        else:
            print "Bailing on DB query, not sure it exists yet"

        self.saveActions = False if self.import_options['saveActions'] == False else True

        self.connection.rollback()  # make sure any locks taken so far are released

    # could be used by hud to change hud style
    def set_hud_style(self, style):
        self.hud_style = style

    def do_connect(self, c):
        self.fdb.do_connect(c)

    def commit(self):
        self.fdb.db.commit()

    def rollback(self):
        self.fdb.db.rollback()

    def get_cursor(self):
        return self.connection.cursor()

    def close_connection(self):
        self.connection.close()

    def disconnect(self, due_to_error=False):
        """Disconnects the DB (rolls back if param is true, otherwise commits"""
        self.fdb.disconnect(due_to_error)
    
    def reconnect(self, due_to_error=False):
        """Reconnects the DB"""
        self.fdb.reconnect(due_to_error=False)
    
    def get_backend_name(self):
        """Reconnects the DB"""
        return self.fdb.get_backend_name()
        

    def get_table_name(self, hand_id):
        c = self.connection.cursor()
        c.execute(self.sql.query['get_table_name'], (hand_id, ))
        row = c.fetchone()
        return row
    
    def get_last_hand(self):
        c = self.connection.cursor()
        c.execute(self.sql.query['get_last_hand'])
        row = c.fetchone()
        return row[0]
    
    def get_xml(self, hand_id):
        c = self.connection.cursor()
        c.execute(self.sql.query['get_xml'], (hand_id))
        row = c.fetchone()
        return row[0]
    
    def get_recent_hands(self, last_hand):
        c = self.connection.cursor()
        c.execute(self.sql.query['get_recent_hands'], {'last_hand': last_hand})
        return c.fetchall()
    
    def get_hand_info(self, new_hand_id):
        c = self.connection.cursor()
        c.execute(self.sql.query['get_hand_info'], new_hand_id)
        return c.fetchall()

    def get_actual_seat(self, hand_id, name):
        c = self.connection.cursor()
        c.execute(self.sql.query['get_actual_seat'], (hand_id, name))
        row = c.fetchone()
        return row[0]

    def get_cards(self, hand):
        """Get and return the cards for each player in the hand."""
        cards = {} # dict of cards, the key is the seat number,
                   # the value is a tuple of the players cards
                   # example: {1: (0, 0, 20, 21, 22, 0 , 0)}
        c = self.connection.cursor()
        c.execute(self.sql.query['get_cards'], [hand])
        for row in c.fetchall():
            cards[row[0]] = row[1:]
        return cards

    def get_common_cards(self, hand):
        """Get and return the community cards for the specified hand."""
        cards = {}
        c = self.connection.cursor()
        c.execute(self.sql.query['get_common_cards'], [hand])
#        row = c.fetchone()
        cards['common'] = c.fetchone()
        return cards

    def convert_cards(self, d):
        ranks = ('', '', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A')
        cards = ""
        for i in xrange(1, 8):
#            key = 'card' + str(i) + 'Value'
#            if not d.has_key(key): continue
#            if d[key] == None:
#                break
#            elif d[key] == 0:
#                cards += "xx"
#            else:
#                cards += ranks[d['card' + str(i) + 'Value']] + d['card' +str(i) + 'Suit']
            cv = "card%dvalue" % i
            if cv not in d or d[cv] == None:
                break
            elif d[cv] == 0:
                cards += "xx"
            else:
                cs = "card%dsuit" % i
                cards = "%s%s%s" % (cards, ranks[d[cv]], d[cs])
        return cards

    def get_action_from_hand(self, hand_no):
        action = [ [], [], [], [], [] ]
        c = self.connection.cursor()
        c.execute(self.sql.query['get_action_from_hand'], (hand_no,))
        for row in c.fetchall():
            street = row[0]
            act = row[1:]
            action[street].append(act)
        return action

    def get_winners_from_hand(self, hand):
        """Returns a hash of winners:amount won, given a hand number."""
        winners = {}
        c = self.connection.cursor()
        c.execute(self.sql.query['get_winners_from_hand'], (hand,))
        for row in c.fetchall():
            winners[row[0]] = row[1]
        return winners

    def get_stats_from_hand(self, hand, aggregate = False):
        if self.hud_style == 'S':
            return( self.get_stats_from_hand_session(hand) )
        else:   # self.hud_style == A
            if aggregate:
                query = 'get_stats_from_hand_aggregated'
            else:
                query = 'get_stats_from_hand'
        
        if self.hud_style == 'T':
            stylekey = self.date_ndays_ago
        else:  # assume A (all-time)
            stylekey = '0000000'  # all stylekey values should be higher than this

        subs = (hand, hand, stylekey)
        #print "get stats: hud style =", self.hud_style, "subs =", subs
        c = self.connection.cursor()

#       now get the stats
        c.execute(self.sql.query[query], subs)
        colnames = [desc[0] for desc in c.description]
        stat_dict = {}
        for row in c.fetchall():
            t_dict = {}
            for name, val in zip(colnames, row):
                t_dict[name.lower()] = val
#                print t_dict
            stat_dict[t_dict['player_id']] = t_dict

        return stat_dict

    # uses query on handsplayers instead of hudcache to get stats on just this session
    def get_stats_from_hand_session(self, hand):

        if self.hud_style == 'S':
            query = self.sql.query['get_stats_from_hand_session']
            if self.db_server == 'mysql':
                query = query.replace("<signed>", 'signed ')
            else:
                query = query.replace("<signed>", '')
        else:   # self.hud_style == A
            return None
        
        subs = (self.hand_1day_ago, hand)
        c = self.connection.cursor()

        # now get the stats
        #print "sess_stats: subs =", subs, "subs[0] =", subs[0]
        c.execute(query, subs)
        colnames = [desc[0] for desc in c.description]
        n,stat_dict = 0,{}
        row = c.fetchone()
        while row:
            if colnames[0].lower() == 'player_id':
                playerid = row[0]
            else:
                print "ERROR: query %s result does not have player_id as first column" % (query,)
                break

            for name, val in zip(colnames, row):
                if not playerid in stat_dict:
                    stat_dict[playerid] = {}
                    stat_dict[playerid][name.lower()] = val
                elif not name.lower() in stat_dict[playerid]:
                    stat_dict[playerid][name.lower()] = val
                elif name.lower() not in ('hand_id', 'player_id', 'seat', 'screen_name', 'seats'):
                    stat_dict[playerid][name.lower()] += val
            n += 1
            if n >= 4000: break  # todo: don't think this is needed so set nice and high 
                                 #       for now - comment out or remove?
            row = c.fetchone()
        #print "   %d rows fetched, len(stat_dict) = %d" % (n, len(stat_dict))

        #print "session stat_dict =", stat_dict
        return stat_dict
            
    def get_player_id(self, config, site, player_name):
        c = self.connection.cursor()
        c.execute(self.sql.query['get_player_id'], {'player': player_name, 'site': site})
        row = c.fetchone()
        if row:
            return row[0]
        else:
            return None

    def get_last_insert_id(self):
        try:
            ret = self.fdb.getLastInsertId()
        except:
            print "get_last_insert_id error:", str(sys.exc_value)
        return ret


    #stores a stud/razz hand into the database
    def ring_stud(self, config, settings, base, category, site_hand_no, gametype_id, hand_start_time
                 ,names, player_ids, start_cashes, antes, card_values, card_suits, winnings, rakes
                 ,action_types, allIns, action_amounts, actionNos, hudImportData, maxSeats, tableName
                 ,seatNos):

        try:
            fpdb_simple.fillCardArrays(len(names), base, category, card_values, card_suits)

            hands_id = self.storeHands(self.backend, site_hand_no, gametype_id
                                      ,hand_start_time, names, tableName, maxSeats, hudImportData
                                      ,(None, None, None, None, None), (None, None, None, None, None))

            #print "before calling store_hands_players_stud, antes:", antes
            hands_players_ids = self.store_hands_players_stud(self.backend, hands_id, player_ids
                                                             ,start_cashes, antes, card_values
                                                             ,card_suits, winnings, rakes, seatNos)

            if 'dropHudCache' not in settings or settings['dropHudCache'] != 'drop':
                self.storeHudCache(self.backend, base, category, gametype_id, hand_start_time, player_ids, hudImportData)

            if self.saveActions:
                fpdb_simple.storeActions(cursor, hands_players_ids, action_types
                                        ,allIns, action_amounts, actionNos)
        except:
            print "ring_stud error: " + str(sys.exc_value)  # in case exception doesn't get printed
            raise fpdb_simple.FpdbError("ring_stud error: " + str(sys.exc_value))
        return hands_id
    #end def ring_stud

    def ring_holdem_omaha(self, config, settings, base, category, site_hand_no, gametype_id
                         ,hand_start_time, names, player_ids, start_cashes, positions, card_values
                         ,card_suits, board_values, board_suits, winnings, rakes, action_types, allIns
                         ,action_amounts, actionNos, hudImportData, maxSeats, tableName, seatNos):
        """stores a holdem/omaha hand into the database"""

        try:
            t0 = time()
            #print "in ring_holdem_omaha"
            fpdb_simple.fillCardArrays(len(names), base, category, card_values, card_suits)
            t1 = time()
            fpdb_simple.fill_board_cards(board_values, board_suits)
            t2 = time()

            hands_id = self.storeHands(self.backend, site_hand_no, gametype_id
                                      ,hand_start_time, names, tableName, maxSeats
                                      ,hudImportData, board_values, board_suits)
            #TEMPORARY CALL! - Just until all functions are migrated
            t3 = time()
            hands_players_ids = self.store_hands_players_holdem_omaha(
                                       self.backend, category, hands_id, player_ids, start_cashes
                                     , positions, card_values, card_suits, winnings, rakes, seatNos, hudImportData)
            t4 = time()
            if 'dropHudCache' not in settings or settings['dropHudCache'] != 'drop':
                self.storeHudCache(self.backend, base, category, gametype_id, hand_start_time, player_ids, hudImportData)
            t5 = time()
            t6 = time()
            if self.saveActions:
                fpdb_simple.storeActions(hands_players_ids, action_types, allIns, action_amounts, actionNos)
            t7 = time()
            #print "fills=(%4.3f) saves=(%4.3f,%4.3f,%4.3f)" % (t2-t0, t3-t2, t4-t3, t5-t4)
        except:
            print "ring_holdem_omaha error: " + str(sys.exc_value)  # in case exception doesn't get printed
            raise fpdb_simple.FpdbError("ring_holdem_omaha error: " + str(sys.exc_value))
        return hands_id
    #end def ring_holdem_omaha

    def tourney_holdem_omaha(self, config, settings, base, category, siteTourneyNo, buyin, fee, knockout
                            ,entries, prizepool, tourney_start, payin_amounts, ranks, tourneyTypeId
                            ,siteId #end of tourney specific params
                            ,site_hand_no, gametype_id, hand_start_time, names, player_ids
                            ,start_cashes, positions, card_values, card_suits, board_values
                            ,board_suits, winnings, rakes, action_types, allIns, action_amounts
                            ,actionNos, hudImportData, maxSeats, tableName, seatNos):
        """stores a tourney holdem/omaha hand into the database"""

        try:
            fpdb_simple.fillCardArrays(len(names), base, category, card_values, card_suits)
            fpdb_simple.fill_board_cards(board_values, board_suits)

            tourney_id = self.store_tourneys(tourneyTypeId, siteTourneyNo, entries, prizepool, tourney_start)
            tourneys_players_ids = self.store_tourneys_players(tourney_id, player_ids, payin_amounts, ranks, winnings)

            hands_id = self.storeHands(self.backend, site_hand_no, gametype_id
                                      ,hand_start_time, names, tableName, maxSeats
                                      ,hudImportData, board_values, board_suits)

            hands_players_ids = self.store_hands_players_holdem_omaha_tourney(
                              self.backend, category, hands_id, player_ids, start_cashes, positions
                            , card_values, card_suits, winnings, rakes, seatNos, tourneys_players_ids
                            , hudImportData)

            #print "tourney holdem, backend=%d" % backend
            if 'dropHudCache' not in settings or settings['dropHudCache'] != 'drop':
                self.storeHudCache(self.backend, base, category, gametype_id, hand_start_time, player_ids, hudImportData)

            if self.saveActions:
                fpdb_simple.storeActions(cursor, hands_players_ids, action_types, allIns, action_amounts, actionNos)
        except:
            print "tourney_holdem_omaha error: " + str(sys.exc_value)  # in case exception doesn't get printed
            raise fpdb_simple.FpdbError("tourney_holdem_omaha error: " + str(sys.exc_value))
        return hands_id
    #end def tourney_holdem_omaha

    def tourney_stud(self, config, settings, base, category, siteTourneyNo, buyin, fee, knockout, entries
                    ,prizepool, tourneyStartTime, payin_amounts, ranks, tourneyTypeId, siteId
                    ,siteHandNo, gametypeId, handStartTime, names, playerIds, startCashes, antes
                    ,cardValues, cardSuits, winnings, rakes, actionTypes, allIns, actionAmounts
                    ,actionNos, hudImportData, maxSeats, tableName, seatNos):
        #stores a tourney stud/razz hand into the database

        try:
            fpdb_simple.fillCardArrays(len(names), base, category, cardValues, cardSuits)

            tourney_id = self.store_tourneys(tourneyTypeId, siteTourneyNo, entries, prizepool, tourneyStartTime)

            tourneys_players_ids = self.store_tourneys_players(tourney_id, playerIds, payin_amounts, ranks, winnings)

            hands_id = self.storeHands( self.backend, siteHandNo, gametypeId
                                      , handStartTime, names, tableName, maxSeats
                                      , hudImportData, board_values, board_suits )

            hands_players_ids = self.store_hands_players_stud_tourney(self.backend, hands_id
                                                     , playerIds, startCashes, antes, cardValues, cardSuits
                                                     , winnings, rakes, seatNos, tourneys_players_ids)

            if 'dropHudCache' not in settings or settings['dropHudCache'] != 'drop':
                self.storeHudCache(self.backend, base, category, gametypeId, hand_start_time, playerIds, hudImportData)

            if self.saveActions:
                fpdb_simple.storeActions(cursor, hands_players_ids, actionTypes, allIns, actionAmounts, actionNos)
        except:
            print "tourney_stud error: " + str(sys.exc_value)  # in case exception doesn't get printed
            raise fpdb_simple.FpdbError("tourney_stud error: " + str(sys.exc_value))

        return hands_id
    #end def tourney_stud

    def rebuild_hudcache(self):
        """clears hudcache and rebuilds from the individual handsplayers records"""

        stime = time()
        self.connection.cursor().execute(self.sql.query['clearHudCache'])
        self.connection.cursor().execute(self.sql.query['rebuildHudCache'])
        self.commit()
        print "Rebuild hudcache took %.1f seconds" % (time() - stime,)
    #end def rebuild_hudcache


    def analyzeDB(self):
        """Do whatever the DB can offer to update index/table statistics"""
        stime = time()
        if self.backend == self.MYSQL_INNODB:
            try:
                self.get_cursor().execute(self.sql.query['analyze'])
            except:
                print "Error during analyze:", str(sys.exc_value)
        elif self.backend == self.PGSQL:
            self.connection.set_isolation_level(0)   # allow vacuum to work
            try:
                self.get_cursor().execute(self.sql.query['analyze'])
            except:
                print "Error during analyze:", str(sys.exc_value)
            self.connection.set_isolation_level(1)   # go back to normal isolation level
        self.commit()
        atime = time() - stime
        print "Analyze took %.1f seconds" % (atime,)
    #end def analyzeDB
    
    def storeActions(self, handsPlayersIds, actionTypes, allIns, actionAmounts, actionNos):
    #stores into table hands_actions
        #print "start of storeActions, actionNos:",actionNos
        #print " action_amounts:",action_amounts
        inserts = []
        for i in xrange(len(actionTypes)): #iterate through streets
            for j in xrange(len(actionTypes[i])): #iterate through names
                for k in xrange(len(actionTypes[i][j])): #iterate through individual actions of that player on that street
                    # Add inserts into a list and let
                    inserts = inserts + [(handsPlayersIds[j], i, actionNos[i][j][k], actionTypes[i][j][k], allIns[i][j][k], actionAmounts[i][j][k])]

        self.get_cursor().executemany("INSERT INTO HandsActions (handsPlayerId, street, actionNo, action, allIn, amount) "
                                     +"VALUES (%s, %s, %s, %s, %s, %s)", inserts)
    #end def storeActions


# Start of Hand Writing routines. Idea is to provide a mixture of routines to store Hand data
# however the calling prog requires. Main aims:
# - existing static routines from fpdb_simple just modified
     
    def storeHands(self, backend, site_hand_no, gametype_id
                  ,hand_start_time, names, tableName, maxSeats, hudCache
                  ,board_values, board_suits):

        cards = [Card.cardFromValueSuit(v,s) for v,s in zip(board_values,board_suits)]
        #stores into table hands:
        try:
            self.get_cursor().execute ("""INSERT INTO Hands 
                                          (siteHandNo, gametypeId, handStart, seats, tableName, importTime, maxSeats
                                          ,boardcard1,boardcard2,boardcard3,boardcard4,boardcard5
                                          ,playersVpi, playersAtStreet1, playersAtStreet2
                                          ,playersAtStreet3, playersAtStreet4, playersAtShowdown
                                          ,street0Raises, street1Raises, street2Raises
                                          ,street3Raises, street4Raises, street1Pot
                                          ,street2Pot, street3Pot, street4Pot
                                          ,showdownPot
                                          ) 
                                          VALUES 
                                          (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                       """
                                      ,   (site_hand_no, gametype_id, hand_start_time, len(names), tableName, datetime.today(), maxSeats
                                          ,cards[0], cards[1], cards[2], cards[3], cards[4]
                                          ,hudCache['playersVpi'], hudCache['playersAtStreet1'], hudCache['playersAtStreet2']
                                          ,hudCache['playersAtStreet3'], hudCache['playersAtStreet4'], hudCache['playersAtShowdown']
                                          ,hudCache['street0Raises'], hudCache['street1Raises'], hudCache['street2Raises']
                                          ,hudCache['street3Raises'], hudCache['street4Raises'], hudCache['street1Pot']
                                          ,hudCache['street2Pot'], hudCache['street3Pot'], hudCache['street4Pot']
                                          ,hudCache['showdownPot']
                                          ))
            ret = self.get_last_insert_id()
        except:
            ret = -1
            raise fpdb_simple.FpdbError( "storeHands error: " + str(sys.exc_value) )

        return ret
    #end def storeHands
     
    def store_hands_players_holdem_omaha(self, backend, category, hands_id, player_ids, start_cashes
                                        ,positions, card_values, card_suits, winnings, rakes, seatNos, hudCache):
        result=[]

        # postgres (and others?) needs the booleans converted to ints before saving:
        # (or we could just save them as boolean ... but then we can't sum them so easily in sql ???)
        # NO - storing booleans for now so don't need this
        #hudCacheInt = {}
        #for k,v in hudCache.iteritems():
        #    if k in ('wonWhenSeenStreet1', 'wonAtSD', 'totalProfit'):
        #        hudCacheInt[k] = v
        #    else:
        #        hudCacheInt[k] = map(lambda x: 1 if x else 0, v)

        try:
            inserts = []
            for i in xrange(len(player_ids)):
                card1 = Card.cardFromValueSuit(card_values[i][0], card_suits[i][0])
                card2 = Card.cardFromValueSuit(card_values[i][1], card_suits[i][1])

                if (category=="holdem"):
                    startCards = Card.twoStartCards(card_values[i][0], card_suits[i][0], card_values[i][1], card_suits[i][1])
                    card3 = None
                    card4 = None
                elif (category=="omahahi" or category=="omahahilo"):
                    startCards = Card.fourStartCards(card_values[i][0], card_suits[i][0], card_values[i][1], card_suits[i][1]
                                                    ,card_values[i][2], card_suits[i][2], card_values[i][3], card_suits[i][3])
                    card3 = Card.cardFromValueSuit(card_values[i][2], card_suits[i][2])
                    card4 = Card.cardFromValueSuit(card_values[i][3], card_suits[i][3])
                else:
                    raise fpdb_simple.FpdbError("invalid category")

                inserts.append( (
                                 hands_id, player_ids[i], start_cashes[i], positions[i], 1, # tourneytypeid
                                 card1, card2, card3, card4, startCards,
                                 winnings[i], rakes[i], seatNos[i], hudCache['totalProfit'][i],
                                 hudCache['street0VPI'][i], hudCache['street0Aggr'][i], 
                                 hudCache['street0_3BChance'][i], hudCache['street0_3BDone'][i],
                                 hudCache['street1Seen'][i], hudCache['street2Seen'][i], hudCache['street3Seen'][i], 
                                 hudCache['street4Seen'][i], hudCache['sawShowdown'][i],
                                 hudCache['street1Aggr'][i], hudCache['street2Aggr'][i], hudCache['street3Aggr'][i], hudCache['street4Aggr'][i],
                                 hudCache['otherRaisedStreet1'][i], hudCache['otherRaisedStreet2'][i], 
                                 hudCache['otherRaisedStreet3'][i], hudCache['otherRaisedStreet4'][i],
                                 hudCache['foldToOtherRaisedStreet1'][i], hudCache['foldToOtherRaisedStreet2'][i], 
                                 hudCache['foldToOtherRaisedStreet3'][i], hudCache['foldToOtherRaisedStreet4'][i],
                                 hudCache['wonWhenSeenStreet1'][i], hudCache['wonAtSD'][i],
                                 hudCache['stealAttemptChance'][i], hudCache['stealAttempted'][i], hudCache['foldBbToStealChance'][i], 
                                 hudCache['foldedBbToSteal'][i], hudCache['foldSbToStealChance'][i], hudCache['foldedSbToSteal'][i],
                                 hudCache['street1CBChance'][i], hudCache['street1CBDone'][i], hudCache['street2CBChance'][i], hudCache['street2CBDone'][i],
                                 hudCache['street3CBChance'][i], hudCache['street3CBDone'][i], hudCache['street4CBChance'][i], hudCache['street4CBDone'][i],
                                 hudCache['foldToStreet1CBChance'][i], hudCache['foldToStreet1CBDone'][i], 
                                 hudCache['foldToStreet2CBChance'][i], hudCache['foldToStreet2CBDone'][i],
                                 hudCache['foldToStreet3CBChance'][i], hudCache['foldToStreet3CBDone'][i], 
                                 hudCache['foldToStreet4CBChance'][i], hudCache['foldToStreet4CBDone'][i],
                                 hudCache['street1CheckCallRaiseChance'][i], hudCache['street1CheckCallRaiseDone'][i], 
                                 hudCache['street2CheckCallRaiseChance'][i], hudCache['street2CheckCallRaiseDone'][i],
                                 hudCache['street3CheckCallRaiseChance'][i], hudCache['street3CheckCallRaiseDone'][i], 
                                 hudCache['street4CheckCallRaiseChance'][i], hudCache['street4CheckCallRaiseDone'][i],
                                 hudCache['street0Calls'][i], hudCache['street1Calls'][i], hudCache['street2Calls'][i], hudCache['street3Calls'][i], hudCache['street4Calls'][i],
                                 hudCache['street0Bets'][i], hudCache['street1Bets'][i], hudCache['street2Bets'][i], hudCache['street3Bets'][i], hudCache['street4Bets'][i]
                                ) )
            self.get_cursor().executemany ("""
        INSERT INTO HandsPlayers
        (handId, playerId, startCash, position, tourneyTypeId,
         card1, card2, card3, card4, startCards, winnings, rake, seatNo, totalProfit,
         street0VPI, street0Aggr, street0_3BChance, street0_3BDone,
         street1Seen, street2Seen, street3Seen, street4Seen, sawShowdown,
         street1Aggr, street2Aggr, street3Aggr, street4Aggr,
         otherRaisedStreet1, otherRaisedStreet2, otherRaisedStreet3, otherRaisedStreet4,
         foldToOtherRaisedStreet1, foldToOtherRaisedStreet2, foldToOtherRaisedStreet3, foldToOtherRaisedStreet4,
         wonWhenSeenStreet1, wonAtSD,
         stealAttemptChance, stealAttempted, foldBbToStealChance, foldedBbToSteal, foldSbToStealChance, foldedSbToSteal,
         street1CBChance, street1CBDone, street2CBChance, street2CBDone,
         street3CBChance, street3CBDone, street4CBChance, street4CBDone,
         foldToStreet1CBChance, foldToStreet1CBDone, foldToStreet2CBChance, foldToStreet2CBDone,
         foldToStreet3CBChance, foldToStreet3CBDone, foldToStreet4CBChance, foldToStreet4CBDone,
         street1CheckCallRaiseChance, street1CheckCallRaiseDone, street2CheckCallRaiseChance, street2CheckCallRaiseDone,
         street3CheckCallRaiseChance, street3CheckCallRaiseDone, street4CheckCallRaiseChance, street4CheckCallRaiseDone,
         street0Calls, street1Calls, street2Calls, street3Calls, street4Calls, 
         street0Bets, street1Bets, street2Bets, street3Bets, street4Bets
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
         %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
         %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
         %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                                          ,inserts )
            result.append( self.get_last_insert_id() )
                
            #cursor.execute("SELECT id FROM HandsPlayers WHERE handId=%s AND playerId+0=%s", (hands_id, player_ids[i]))
            #result.append(cursor.fetchall()[0][0])
            result.append( self.get_last_insert_id() )
        except:
            raise fpdb_simple.FpdbError( "store_hands_players_holdem_omaha error: " + str(sys.exc_value) )

        return result
    #end def store_hands_players_holdem_omaha

    def store_hands_players_stud(self, backend, hands_id, player_ids, start_cashes, antes,
                                 card_values, card_suits, winnings, rakes, seatNos):
        #stores hands_players rows for stud/razz games. returns an array of the resulting IDs

        try:
            result=[]
            #print "before inserts in store_hands_players_stud, antes:", antes
            for i in xrange(len(player_ids)):
                card1 = Card.cardFromValueSuit(card_values[i][0], card_suits[i][0])
                card2 = Card.cardFromValueSuit(card_values[i][1], card_suits[i][1])
                card3 = Card.cardFromValueSuit(card_values[i][2], card_suits[i][2])
                card4 = Card.cardFromValueSuit(card_values[i][3], card_suits[i][3])
                card5 = Card.cardFromValueSuit(card_values[i][4], card_suits[i][4])
                card6 = Card.cardFromValueSuit(card_values[i][5], card_suits[i][5])
                card7 = Card.cardFromValueSuit(card_values[i][6], card_suits[i][6])

                self.get_cursor().execute ("""INSERT INTO HandsPlayers
        (handId, playerId, startCash, ante, tourneyTypeId,
        card1, card2,
        card3, card4,
        card5, card6,
        card7, winnings, rake, seatNo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (hands_id, player_ids[i], start_cashes[i], antes[i], 1, 
                card1, card2,
                card3, card4,
                card5, card6,
                card7, winnings[i], rakes[i], seatNos[i]))
                #cursor.execute("SELECT id FROM HandsPlayers WHERE handId=%s AND playerId+0=%s", (hands_id, player_ids[i]))
                #result.append(cursor.fetchall()[0][0])
                result.append( self.get_last_insert_id() )
        except:
            raise fpdb_simple.FpdbError( "store_hands_players_stud error: " + str(sys.exc_value) )

        return result
    #end def store_hands_players_stud
     
    def store_hands_players_holdem_omaha_tourney(self, backend, category, hands_id, player_ids
                                                ,start_cashes, positions, card_values, card_suits
                                                ,winnings, rakes, seatNos, tourneys_players_ids
                                                ,hudCache):
        #stores hands_players for tourney holdem/omaha hands

        try:
            result=[]
            inserts = []
            for i in xrange(len(player_ids)):
                card1 = Card.cardFromValueSuit(card_values[i][0], card_suits[i][0])
                card2 = Card.cardFromValueSuit(card_values[i][1], card_suits[i][1])

                if len(card_values[0])==2:
                    startCards = Card.twoStartCards(card_values[i][0], card_suits[i][0], card_values[i][1], card_suits[i][1])
                    card3 = None
                    card4 = None
                elif len(card_values[0])==4:
                    startCards = Card.fourStartCards(card_values[i][0], card_suits[i][0], card_values[i][1], card_suits[i][1]
                                                    ,card_values[i][2], card_suits[i][2], card_values[i][3], card_suits[i][3])
                    card3 = Card.cardFromValueSuit(card_values[i][2], card_suits[i][2])
                    card4 = Card.cardFromValueSuit(card_values[i][3], card_suits[i][3])
                else:
                    raise FpdbError ("invalid card_values length:"+str(len(card_values[0])))

                inserts.append( (hands_id, player_ids[i], start_cashes[i], positions[i], 1, # tourneytypeid
                                 card1, card2, card3, card4, startCards,
                                 winnings[i], rakes[i], tourneys_players_ids[i], seatNos[i], hudCache['totalProfit'][i],
                                 hudCache['street0VPI'][i], hudCache['street0Aggr'][i], 
                                 hudCache['street0_3BChance'][i], hudCache['street0_3BDone'][i],
                                 hudCache['street1Seen'][i], hudCache['street2Seen'][i], hudCache['street3Seen'][i], 
                                 hudCache['street4Seen'][i], hudCache['sawShowdown'][i],
                                 hudCache['street1Aggr'][i], hudCache['street2Aggr'][i], hudCache['street3Aggr'][i], hudCache['street4Aggr'][i],
                                 hudCache['otherRaisedStreet1'][i], hudCache['otherRaisedStreet2'][i], 
                                 hudCache['otherRaisedStreet3'][i], hudCache['otherRaisedStreet4'][i],
                                 hudCache['foldToOtherRaisedStreet1'][i], hudCache['foldToOtherRaisedStreet2'][i], 
                                 hudCache['foldToOtherRaisedStreet3'][i], hudCache['foldToOtherRaisedStreet4'][i],
                                 hudCache['wonWhenSeenStreet1'][i], hudCache['wonAtSD'][i],
                                 hudCache['stealAttemptChance'][i], hudCache['stealAttempted'][i], hudCache['foldBbToStealChance'][i], 
                                 hudCache['foldedBbToSteal'][i], hudCache['foldSbToStealChance'][i], hudCache['foldedSbToSteal'][i],
                                 hudCache['street1CBChance'][i], hudCache['street1CBDone'][i], hudCache['street2CBChance'][i], hudCache['street2CBDone'][i],
                                 hudCache['street3CBChance'][i], hudCache['street3CBDone'][i], hudCache['street4CBChance'][i], hudCache['street4CBDone'][i],
                                 hudCache['foldToStreet1CBChance'][i], hudCache['foldToStreet1CBDone'][i], 
                                 hudCache['foldToStreet2CBChance'][i], hudCache['foldToStreet2CBDone'][i],
                                 hudCache['foldToStreet3CBChance'][i], hudCache['foldToStreet3CBDone'][i], 
                                 hudCache['foldToStreet4CBChance'][i], hudCache['foldToStreet4CBDone'][i],
                                 hudCache['street1CheckCallRaiseChance'][i], hudCache['street1CheckCallRaiseDone'][i], 
                                 hudCache['street2CheckCallRaiseChance'][i], hudCache['street2CheckCallRaiseDone'][i],
                                 hudCache['street3CheckCallRaiseChance'][i], hudCache['street3CheckCallRaiseDone'][i], 
                                 hudCache['street4CheckCallRaiseChance'][i], hudCache['street4CheckCallRaiseDone'][i],
                                 hudCache['street0Calls'][i], hudCache['street1Calls'][i], hudCache['street2Calls'][i], 
                                 hudCache['street3Calls'][i], hudCache['street4Calls'][i],
                                 hudCache['street0Bets'][i], hudCache['street1Bets'][i], hudCache['street2Bets'][i], 
                                 hudCache['street3Bets'][i], hudCache['street4Bets'][i]
                                ) )

            self.get_cursor().executemany ("""
        INSERT INTO HandsPlayers
        (handId, playerId, startCash, position, tourneyTypeId,
         card1, card2, card3, card4, startCards, winnings, rake, tourneysPlayersId, seatNo, totalProfit,
         street0VPI, street0Aggr, street0_3BChance, street0_3BDone,
         street1Seen, street2Seen, street3Seen, street4Seen, sawShowdown,
         street1Aggr, street2Aggr, street3Aggr, street4Aggr,
         otherRaisedStreet1, otherRaisedStreet2, otherRaisedStreet3, otherRaisedStreet4,
         foldToOtherRaisedStreet1, foldToOtherRaisedStreet2, foldToOtherRaisedStreet3, foldToOtherRaisedStreet4,
         wonWhenSeenStreet1, wonAtSD,
         stealAttemptChance, stealAttempted, foldBbToStealChance, foldedBbToSteal, foldSbToStealChance, foldedSbToSteal,
         street1CBChance, street1CBDone, street2CBChance, street2CBDone,
         street3CBChance, street3CBDone, street4CBChance, street4CBDone,
         foldToStreet1CBChance, foldToStreet1CBDone, foldToStreet2CBChance, foldToStreet2CBDone,
         foldToStreet3CBChance, foldToStreet3CBDone, foldToStreet4CBChance, foldToStreet4CBDone,
         street1CheckCallRaiseChance, street1CheckCallRaiseDone, street2CheckCallRaiseChance, street2CheckCallRaiseDone,
         street3CheckCallRaiseChance, street3CheckCallRaiseDone, street4CheckCallRaiseChance, street4CheckCallRaiseDone,
         street0Calls, street1Calls, street2Calls, street3Calls, street4Calls, 
         street0Bets, street1Bets, street2Bets, street3Bets, street4Bets
        )
        VALUES 
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
         %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
         %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
         %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                                          ,inserts )

            result.append( self.get_last_insert_id() )
            #cursor.execute("SELECT id FROM HandsPlayers WHERE handId=%s AND playerId+0=%s", (hands_id, player_ids[i]))
            #result.append(cursor.fetchall()[0][0])
        except:
            raise fpdb_simple.FpdbError( "store_hands_players_holdem_omaha_tourney error: " + str(sys.exc_value) )
        
        return result
    #end def store_hands_players_holdem_omaha_tourney
     
    def store_hands_players_stud_tourney(self, backend, hands_id, player_ids, start_cashes,
                antes, card_values, card_suits, winnings, rakes, seatNos, tourneys_players_ids):
        #stores hands_players for tourney stud/razz hands

        try:
            result=[]
            for i in xrange(len(player_ids)):
                self.get_cursor().execute ("""INSERT INTO HandsPlayers
        (handId, playerId, startCash, ante,
        card1Value, card1Suit, card2Value, card2Suit,
        card3Value, card3Suit, card4Value, card4Suit,
        card5Value, card5Suit, card6Value, card6Suit,
        card7Value, card7Suit, winnings, rake, tourneysPlayersId, seatNo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s)""",
                (hands_id, player_ids[i], start_cashes[i], antes[i],
                card_values[i][0], card_suits[i][0], card_values[i][1], card_suits[i][1],
                card_values[i][2], card_suits[i][2], card_values[i][3], card_suits[i][3],
                card_values[i][4], card_suits[i][4], card_values[i][5], card_suits[i][5],
                card_values[i][6], card_suits[i][6], winnings[i], rakes[i], tourneys_players_ids[i], seatNos[i]))
                #cursor.execute("SELECT id FROM HandsPlayers WHERE handId=%s AND playerId+0=%s", (hands_id, player_ids[i]))
                #result.append(cursor.fetchall()[0][0])
                result.append( self.get_last_insert_id() )
        except:
            raise fpdb_simple.FpdbError( "store_hands_players_stud_tourney error: " + str(sys.exc_value) )
        
        return result
    #end def store_hands_players_stud_tourney
 
    def storeHudCache(self, backend, base, category, gametypeId, hand_start_time, playerIds, hudImportData):
        """Update cached statistics. If update fails because no record exists, do an insert.
           Can't use array updates here (not easily anyway) because we need to insert any rows
           that don't get updated."""

        # if (category=="holdem" or category=="omahahi" or category=="omahahilo"):
        try:
            if self.use_date_in_hudcache:
                #print "key =", "d%02d%02d%02d " % (hand_start_time.year-2000, hand_start_time.month, hand_start_time.day)
                styleKey = "d%02d%02d%02d" % (hand_start_time.year-2000, hand_start_time.month, hand_start_time.day)
            else:
                # hard-code styleKey as 'A000000' (all-time cache, no key) for now
                styleKey = 'A000000'
            
            #print "storeHudCache, len(playerIds)=", len(playerIds), " len(vpip)=" \
            #, len(hudImportData['street0VPI']), " len(totprof)=", len(hudImportData['totalProfit'])
            for player in xrange(len(playerIds)):
                
                # Set up a clean row
                row=[]
                row.append(0)#blank for id
                row.append(gametypeId)
                row.append(playerIds[player])
                row.append(len(playerIds))#seats
                for i in xrange(len(hudImportData)+2):
                    row.append(0)
                    
                if base=="hold":
                    row[4]=hudImportData['position'][player]
                else:
                    row[4]=0
                row[5]=1 #tourneysGametypeId
                row[6]+=1 #HDs
                if hudImportData['street0VPI'][player]: row[7]+=1
                if hudImportData['street0Aggr'][player]: row[8]+=1
                if hudImportData['street0_3BChance'][player]: row[9]+=1
                if hudImportData['street0_3BDone'][player]: row[10]+=1
                if hudImportData['street1Seen'][player]: row[11]+=1
                if hudImportData['street2Seen'][player]: row[12]+=1
                if hudImportData['street3Seen'][player]: row[13]+=1
                if hudImportData['street4Seen'][player]: row[14]+=1
                if hudImportData['sawShowdown'][player]: row[15]+=1
                if hudImportData['street1Aggr'][player]: row[16]+=1
                if hudImportData['street2Aggr'][player]: row[17]+=1
                if hudImportData['street3Aggr'][player]: row[18]+=1
                if hudImportData['street4Aggr'][player]: row[19]+=1
                if hudImportData['otherRaisedStreet1'][player]: row[20]+=1
                if hudImportData['otherRaisedStreet2'][player]: row[21]+=1
                if hudImportData['otherRaisedStreet3'][player]: row[22]+=1
                if hudImportData['otherRaisedStreet4'][player]: row[23]+=1
                if hudImportData['foldToOtherRaisedStreet1'][player]: row[24]+=1
                if hudImportData['foldToOtherRaisedStreet2'][player]: row[25]+=1
                if hudImportData['foldToOtherRaisedStreet3'][player]: row[26]+=1
                if hudImportData['foldToOtherRaisedStreet4'][player]: row[27]+=1
                if hudImportData['wonWhenSeenStreet1'][player]!=0.0: row[28]+=hudImportData['wonWhenSeenStreet1'][player]
                if hudImportData['wonAtSD'][player]!=0.0: row[29]+=hudImportData['wonAtSD'][player]
                if hudImportData['stealAttemptChance'][player]: row[30]+=1
                if hudImportData['stealAttempted'][player]: row[31]+=1
                if hudImportData['foldBbToStealChance'][player]: row[32]+=1
                if hudImportData['foldedBbToSteal'][player]: row[33]+=1
                if hudImportData['foldSbToStealChance'][player]: row[34]+=1
                if hudImportData['foldedSbToSteal'][player]: row[35]+=1
                
                if hudImportData['street1CBChance'][player]: row[36]+=1
                if hudImportData['street1CBDone'][player]: row[37]+=1
                if hudImportData['street2CBChance'][player]: row[38]+=1
                if hudImportData['street2CBDone'][player]: row[39]+=1
                if hudImportData['street3CBChance'][player]: row[40]+=1
                if hudImportData['street3CBDone'][player]: row[41]+=1
                if hudImportData['street4CBChance'][player]: row[42]+=1
                if hudImportData['street4CBDone'][player]: row[43]+=1
                
                if hudImportData['foldToStreet1CBChance'][player]: row[44]+=1
                if hudImportData['foldToStreet1CBDone'][player]: row[45]+=1
                if hudImportData['foldToStreet2CBChance'][player]: row[46]+=1
                if hudImportData['foldToStreet2CBDone'][player]: row[47]+=1
                if hudImportData['foldToStreet3CBChance'][player]: row[48]+=1
                if hudImportData['foldToStreet3CBDone'][player]: row[49]+=1
                if hudImportData['foldToStreet4CBChance'][player]: row[50]+=1
                if hudImportData['foldToStreet4CBDone'][player]: row[51]+=1
     
                #print "player=", player
                #print "len(totalProfit)=", len(hudImportData['totalProfit'])
                if hudImportData['totalProfit'][player]:
                    row[52]+=hudImportData['totalProfit'][player]
     
                if hudImportData['street1CheckCallRaiseChance'][player]: row[53]+=1
                if hudImportData['street1CheckCallRaiseDone'][player]: row[54]+=1
                if hudImportData['street2CheckCallRaiseChance'][player]: row[55]+=1
                if hudImportData['street2CheckCallRaiseDone'][player]: row[56]+=1
                if hudImportData['street3CheckCallRaiseChance'][player]: row[57]+=1
                if hudImportData['street3CheckCallRaiseDone'][player]: row[58]+=1
                if hudImportData['street4CheckCallRaiseChance'][player]: row[59]+=1
                if hudImportData['street4CheckCallRaiseDone'][player]: row[60]+=1
                
                # Try to do the update first:
                cursor = self.get_cursor()
                num = cursor.execute("""UPDATE HudCache
    SET HDs=HDs+%s, street0VPI=street0VPI+%s, street0Aggr=street0Aggr+%s,
        street0_3BChance=street0_3BChance+%s, street0_3BDone=street0_3BDone+%s,
        street1Seen=street1Seen+%s, street2Seen=street2Seen+%s, street3Seen=street3Seen+%s,
        street4Seen=street4Seen+%s, sawShowdown=sawShowdown+%s,
        street1Aggr=street1Aggr+%s, street2Aggr=street2Aggr+%s, street3Aggr=street3Aggr+%s,
        street4Aggr=street4Aggr+%s, otherRaisedStreet1=otherRaisedStreet1+%s,
        otherRaisedStreet2=otherRaisedStreet2+%s, otherRaisedStreet3=otherRaisedStreet3+%s,
        otherRaisedStreet4=otherRaisedStreet4+%s,
        foldToOtherRaisedStreet1=foldToOtherRaisedStreet1+%s, foldToOtherRaisedStreet2=foldToOtherRaisedStreet2+%s,
        foldToOtherRaisedStreet3=foldToOtherRaisedStreet3+%s, foldToOtherRaisedStreet4=foldToOtherRaisedStreet4+%s,
        wonWhenSeenStreet1=wonWhenSeenStreet1+%s, wonAtSD=wonAtSD+%s, stealAttemptChance=stealAttemptChance+%s,
        stealAttempted=stealAttempted+%s, foldBbToStealChance=foldBbToStealChance+%s,
        foldedBbToSteal=foldedBbToSteal+%s,
        foldSbToStealChance=foldSbToStealChance+%s, foldedSbToSteal=foldedSbToSteal+%s,
        street1CBChance=street1CBChance+%s, street1CBDone=street1CBDone+%s, street2CBChance=street2CBChance+%s,
        street2CBDone=street2CBDone+%s, street3CBChance=street3CBChance+%s,
        street3CBDone=street3CBDone+%s, street4CBChance=street4CBChance+%s, street4CBDone=street4CBDone+%s,
        foldToStreet1CBChance=foldToStreet1CBChance+%s, foldToStreet1CBDone=foldToStreet1CBDone+%s,
        foldToStreet2CBChance=foldToStreet2CBChance+%s, foldToStreet2CBDone=foldToStreet2CBDone+%s,
        foldToStreet3CBChance=foldToStreet3CBChance+%s,
        foldToStreet3CBDone=foldToStreet3CBDone+%s, foldToStreet4CBChance=foldToStreet4CBChance+%s,
        foldToStreet4CBDone=foldToStreet4CBDone+%s, totalProfit=totalProfit+%s,
        street1CheckCallRaiseChance=street1CheckCallRaiseChance+%s,
        street1CheckCallRaiseDone=street1CheckCallRaiseDone+%s, street2CheckCallRaiseChance=street2CheckCallRaiseChance+%s,
        street2CheckCallRaiseDone=street2CheckCallRaiseDone+%s, street3CheckCallRaiseChance=street3CheckCallRaiseChance+%s,
        street3CheckCallRaiseDone=street3CheckCallRaiseDone+%s, street4CheckCallRaiseChance=street4CheckCallRaiseChance+%s,
        street4CheckCallRaiseDone=street4CheckCallRaiseDone+%s
    WHERE gametypeId+0=%s 
    AND   playerId=%s 
    AND   activeSeats=%s 
    AND   position=%s 
    AND   tourneyTypeId+0=%s
    AND   styleKey=%s
                          """, (row[6], row[7], row[8], row[9], row[10],
                                row[11], row[12], row[13], row[14], row[15],
                                row[16], row[17], row[18], row[19], row[20],
                                row[21], row[22], row[23], row[24], row[25],
                                row[26], row[27], row[28], row[29], row[30],
                                row[31], row[32], row[33], row[34], row[35],
                                row[36], row[37], row[38], row[39], row[40],
                                row[41], row[42], row[43], row[44], row[45],
                                row[46], row[47], row[48], row[49], row[50],
                                row[51], row[52], row[53], row[54], row[55],
                                row[56], row[57], row[58], row[59], row[60],
                                row[1], row[2], row[3], str(row[4]), row[5], styleKey))
                # Test statusmessage to see if update worked, do insert if not
                #print "storehud2, upd num =", num
                if (   (backend == self.PGSQL and cursor.statusmessage != "UPDATE 1")
                    or (backend == self.MYSQL_INNODB and num == 0) ):
                    #print "playerid before insert:",row[2]," num = ", num
                    cursor.execute("""INSERT INTO HudCache
    (gametypeId, playerId, activeSeats, position, tourneyTypeId, styleKey,
    HDs, street0VPI, street0Aggr, street0_3BChance, street0_3BDone,
    street1Seen, street2Seen, street3Seen, street4Seen, sawShowdown,
    street1Aggr, street2Aggr, street3Aggr, street4Aggr, otherRaisedStreet1,
    otherRaisedStreet2, otherRaisedStreet3, otherRaisedStreet4, foldToOtherRaisedStreet1, foldToOtherRaisedStreet2,
    foldToOtherRaisedStreet3, foldToOtherRaisedStreet4, wonWhenSeenStreet1, wonAtSD, stealAttemptChance,
    stealAttempted, foldBbToStealChance, foldedBbToSteal, foldSbToStealChance, foldedSbToSteal,
    street1CBChance, street1CBDone, street2CBChance, street2CBDone, street3CBChance,
    street3CBDone, street4CBChance, street4CBDone, foldToStreet1CBChance, foldToStreet1CBDone,
    foldToStreet2CBChance, foldToStreet2CBDone, foldToStreet3CBChance, foldToStreet3CBDone, foldToStreet4CBChance,
    foldToStreet4CBDone, totalProfit, street1CheckCallRaiseChance, street1CheckCallRaiseDone, street2CheckCallRaiseChance,
    street2CheckCallRaiseDone, street3CheckCallRaiseChance, street3CheckCallRaiseDone, street4CheckCallRaiseChance, street4CheckCallRaiseDone)
    VALUES (%s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s)"""
                                  , (row[1], row[2], row[3], row[4], row[5], styleKey, row[6], row[7], row[8], row[9], row[10]
                                    ,row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19], row[20]
                                    ,row[21], row[22], row[23], row[24], row[25], row[26], row[27], row[28], row[29], row[30]
                                    ,row[31], row[32], row[33], row[34], row[35], row[36], row[37], row[38], row[39], row[40]
                                    ,row[41], row[42], row[43], row[44], row[45], row[46], row[47], row[48], row[49], row[50]
                                    ,row[51], row[52], row[53], row[54], row[55], row[56], row[57], row[58], row[59], row[60]) )
                    #print "hopefully inserted hud data line: ", cursor.statusmessage
                    # message seems to be "INSERT 0 1"
                else:
                    #print "updated(2) hud data line"
                    pass
        # else:
        # print "todo: implement storeHudCache for stud base"

        except:
            raise fpdb_simple.FpdbError( "storeHudCache error: " + str(sys.exc_value) )
        
    #end def storeHudCache
 
    def store_tourneys(self, tourneyTypeId, siteTourneyNo, entries, prizepool, startTime):
        try:
            cursor = self.get_cursor()
            cursor.execute("SELECT id FROM Tourneys WHERE siteTourneyNo=%s AND tourneyTypeId+0=%s", (siteTourneyNo, tourneyTypeId))
            tmp=cursor.fetchone()
            #print "tried SELECTing tourneys.id, result:",tmp
            
            try:
                len(tmp)
            except TypeError:#means we have to create new one
                cursor.execute("""INSERT INTO Tourneys
        (tourneyTypeId, siteTourneyNo, entries, prizepool, startTime)
        VALUES (%s, %s, %s, %s, %s)""", (tourneyTypeId, siteTourneyNo, entries, prizepool, startTime))
                cursor.execute("SELECT id FROM Tourneys WHERE siteTourneyNo=%s AND tourneyTypeId+0=%s", (siteTourneyNo, tourneyTypeId))
                tmp=cursor.fetchone()
                #print "created new tourneys.id:",tmp
        except:
            raise fpdb_simple.FpdbError( "store_tourneys error: " + str(sys.exc_value) )
        
        return tmp[0]
    #end def store_tourneys

    def store_tourneys_players(self, tourney_id, player_ids, payin_amounts, ranks, winnings):
        try:
            result=[]
            cursor = self.get_cursor()
            #print "in store_tourneys_players. tourney_id:",tourney_id
            #print "player_ids:",player_ids
            #print "payin_amounts:",payin_amounts
            #print "ranks:",ranks
            #print "winnings:",winnings
            for i in xrange(len(player_ids)):
                cursor.execute("SELECT id FROM TourneysPlayers WHERE tourneyId=%s AND playerId+0=%s", (tourney_id, player_ids[i]))
                tmp=cursor.fetchone()
                #print "tried SELECTing tourneys_players.id:",tmp
                
                try:
                    len(tmp)
                except TypeError:
                    cursor.execute("""INSERT INTO TourneysPlayers
        (tourneyId, playerId, payinAmount, rank, winnings) VALUES (%s, %s, %s, %s, %s)""",
                    (tourney_id, player_ids[i], payin_amounts[i], ranks[i], winnings[i]))
                    
                    cursor.execute("SELECT id FROM TourneysPlayers WHERE tourneyId=%s AND playerId+0=%s",
                                   (tourney_id, player_ids[i]))
                    tmp=cursor.fetchone()
                    #print "created new tourneys_players.id:",tmp
                result.append(tmp[0])
        except:
            raise fpdb_simple.FpdbError( "store_tourneys_players error: " + str(sys.exc_value) )
        
        return result
    #end def store_tourneys_players


class HandToWrite:

    def __init__(self, finished = False): # db_name and game not used any more
        self.finished = finished
        self.config = None
        self.settings = None
        self.base = None
        self.category = None
        self.siteHandNo = None
        self.gametypeID = None
        self.handStartTime = None
        self.names = None
        self.playerIDs = None
        self.startCashes = None
        self.positions = None
        self.cardValues = None
        self.cardSuits = None
        self.boardValues = None
        self.boardSuits = None
        self.winnings = None
        self.rakes = None
        self.actionTypes = None
        self.allIns = None
        self.actionAmounts = None
        self.actionNos = None
        self.hudImportData = None
        self.maxSeats = None
        self.tableName = None
        self.seatNos = None

    def set_ring_holdem_omaha( self, config, settings, base, category, siteHandNo
                             , gametypeID, handStartTime, names, playerIDs
                             , startCashes, positions, cardValues, cardSuits
                             , boardValues, boardSuits, winnings, rakes
                             , actionTypes, allIns, actionAmounts, actionNos
                             , hudImportData, maxSeats, tableName, seatNos ):
        self.config = config
        self.settings = settings
        self.base = base
        self.category = category
        self.siteHandNo = siteHandNo
        self.gametypeID = gametypeID
        self.handStartTime = handStartTime
        self.names = names
        self.playerIDs = playerIDs
        self.startCashes = startCashes
        self.positions = positions
        self.cardValues = cardValues
        self.cardSuits = cardSuits
        self.boardValues = boardValues
        self.boardSuits = boardSuits
        self.winnings = winnings
        self.rakes = rakes
        self.actionTypes = actionTypes
        self.allIns = allIns
        self.actionAmounts = actionAmounts
        self.actionNos = actionNos
        self.hudImportData = hudImportData
        self.maxSeats = maxSeats
        self.tableName = tableName
        self.seatNos = seatNos

    def send_ring_holdem_omaha(self, db):
        result = db.ring_holdem_omaha(
                                   self.config, self.settings, self.base, self.category, self.siteHandNo
                                 , self.gametypeID, self.handStartTime, self.names, self.playerIDs
                                 , self.startCashes, self.positions, self.cardValues, self.cardSuits
                                 , self.boardValues, self.boardSuits, self.winnings, self.rakes
                                 , self.actionTypes, self.allIns, self.actionAmounts, self.actionNos
                                 , self.hudImportData, self.maxSeats, self.tableName, self.seatNos)

    def get_finished(self):
        return( self.finished )

    def get_siteHandNo(self):
        return( self.siteHandNo )


if __name__=="__main__":
    c = Configuration.Config()

    db_connection = Database(c, 'fpdb', 'holdem') # mysql fpdb holdem
#    db_connection = Database(c, 'fpdb-p', 'test') # mysql fpdb holdem
#    db_connection = Database(c, 'PTrackSv2', 'razz') # mysql razz
#    db_connection = Database(c, 'ptracks', 'razz') # postgres
    print "database connection object = ", db_connection.connection
    print "database type = ", db_connection.type
    
    h = db_connection.get_last_hand()
    print "last hand = ", h
    
    hero = db_connection.get_player_id(c, 'PokerStars', 'nutOmatic')
    if hero:
        print "nutOmatic is id_player = %d" % hero
    
    stat_dict = db_connection.get_stats_from_hand(h)
    for p in stat_dict.keys():
        print p, "  ", stat_dict[p]
        
    #print "nutOmatics stats:"
    #stat_dict = db_connection.get_stats_from_hand(h, hero)
    #for p in stat_dict.keys():
    #    print p, "  ", stat_dict[p]

    print "cards =", db_connection.get_cards(u'1')
    db_connection.close_connection

    print "press enter to continue"
    sys.stdin.readline()
