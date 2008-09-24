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

#    pyGTK modules

#    FreePokerTools modules
import Configuration
import SQL

#    pgdb database module for posgres via DB-API
import psycopg2
#    pgdb uses pyformat.  is that fixed or an option?

#    mysql bindings
import MySQLdb

class Database:
    def __init__(self, c, db_name, game):
        if   c.supported_databases[db_name].db_server == 'postgresql':
            self.connection = psycopg2.connect(host = c.supported_databases[db_name].db_ip,
                                       user = c.supported_databases[db_name].db_user,
                                       password = c.supported_databases[db_name].db_pass,
                                       database = c.supported_databases[db_name].db_name)

        elif c.supported_databases[db_name].db_server == 'mysql':
            self.connection = MySQLdb.connect(host = c.supported_databases[db_name].db_ip,
                                       user = c.supported_databases[db_name].db_user,
                                       passwd = c.supported_databases[db_name].db_pass,
                                       db = c.supported_databases[db_name].db_name)

        else:
            print "Database not recognized."
            return(0)

        self.type = c.supported_databases[db_name].db_type
        self.sql = SQL.Sql(game = game, type = self.type)
        
    def close_connection(self):
        self.connection.close()
        
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

#    def get_cards(self, hand):
#    this version is for the PTrackSv2 db
#        c = self.connection.cursor()
#        c.execute(self.sql.query['get_cards'], hand)
#        colnames = [desc[0] for desc in c.description]
#        cards = {}
#        for row in c.fetchall():
#            s_dict = {}
#            for name, val in zip(colnames, row):
#                s_dict[name] = val
#            cards[s_dict['seat_number']] = s_dict
#        return (cards)

    def get_cards(self, hand):
#    this version is for the fpdb db
        c = self.connection.cursor()
        c.execute(self.sql.query['get_cards'], hand)
        colnames = [desc[0] for desc in c.description]
        cards = {}
        for row in c.fetchall():
            s_dict = {}
            for name, val in zip(colnames, row):
                s_dict[name] = val
            cards[s_dict['seat_number']] = s_dict
        return (cards)

    def get_stats_from_hand(self, hand, player_id = False):
        c = self.connection.cursor()

        if not player_id: player_id = "%"
#    get the players in the hand and their seats
#        c.execute(self.sql.query['get_players_from_hand'], (hand, player_id))
        c.execute(self.sql.query['get_players_from_hand'], (hand, ))
        names = {}
        seats = {}
        for row in c.fetchall():
            names[row[0]] = row[2]
            seats[row[0]] = row[1]

#    now get the stats
#        c.execute(self.sql.query['get_stats_from_hand'], (hand, hand, player_id))
        c.execute(self.sql.query['get_stats_from_hand'], (hand, hand))
        colnames = [desc[0] for desc in c.description]
        stat_dict = {}
        for row in c.fetchall():
            t_dict = {}
            for name, val in zip(colnames, row):
                t_dict[name] = val
#                print t_dict
            t_dict['screen_name'] = names[t_dict['player_id']]
            t_dict['seat']        = seats[t_dict['player_id']]
            stat_dict[t_dict['player_id']] = t_dict
        return stat_dict
            
    def get_player_id(self, config, site, player_name):
        print "site  = %s, player name = %s" % (site, player_name)
        c = self.connection.cursor()
        c.execute(self.sql.query['get_player_id'], {'player': player_name, 'site': site})
        row = c.fetchone()
        return row[0]

if __name__=="__main__":
    c = Configuration.Config()

#    db_connection = Database(c, 'fpdb', 'holdem') # mysql fpdb holdem
    db_connection = Database(c, 'fpdb-p', 'test') # mysql fpdb holdem
#    db_connection = Database(c, 'PTrackSv2', 'razz') # mysql razz
#    db_connection = Database(c, 'ptracks', 'razz') # postgres
    print "database connection object = ", db_connection.connection
    print "database type = ", db_connection.type
    
    h = db_connection.get_last_hand()
    print "last hand = ", h
    
    hero = db_connection.get_player_id(c, 'PokerStars', 'nutOmatic')
    print "nutOmatic is id_player = %d" % hero
    
    stat_dict = db_connection.get_stats_from_hand(h)
    for p in stat_dict.keys():
        print p, "  ", stat_dict[p]
        
    print "nutOmatics stats:"
    stat_dict = db_connection.get_stats_from_hand(h, hero)
    for p in stat_dict.keys():
        print p, "  ", stat_dict[p]

    db_connection.close_connection

    print "press enter to continue"
    sys.stdin.readline()