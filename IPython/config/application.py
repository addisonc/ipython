# encoding: utf-8
"""
A base class for a configurable application.

Authors:

* Brian Granger
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2008-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from copy import deepcopy
import logging
import sys

from IPython.config.configurable import SingletonConfigurable
from IPython.config.loader import (
    KeyValueConfigLoader, PyFileConfigLoader, Config
)

from IPython.utils.traitlets import (
    Unicode, List, Int, Enum, Dict
)
from IPython.utils.text import indent

#-----------------------------------------------------------------------------
# Descriptions for
#-----------------------------------------------------------------------------

flag_description = """
Flags are command-line arguments passed as '--<flag>'.
These take no parameters, unlike regular key-value arguments.
They are typically used for setting boolean flags, or enabling
modes that involve setting multiple options together.
""".strip() # trim newlines of front and back

alias_description = """
These are commonly set parameters, given abbreviated aliases for convenience.
They are set in the same `name=value` way as class parameters, where
<name> is replaced by the real parameter for which it is an alias.
""".strip() # trim newlines of front and back

keyvalue_description = """
Parameters are set from command-line arguments of the form:
`Class.trait=value`.  Parameters will *never* be prefixed with '-'.
This line is evaluated in Python, so simple expressions are allowed, e.g.
    `C.a='range(3)'`   For setting C.a=[0,1,2]
""".strip() # trim newlines of front and back

#-----------------------------------------------------------------------------
# Application class
#-----------------------------------------------------------------------------


class Application(SingletonConfigurable):
    """A singleton application with full configuration support."""

    # The name of the application, will usually match the name of the command
    # line application
    app_name = Unicode(u'application')

    # The description of the application that is printed at the beginning
    # of the help.
    description = Unicode(u'This is an application.')
    # default section descriptions
    flag_description = Unicode(flag_description)
    alias_description = Unicode(alias_description)
    keyvalue_description = Unicode(keyvalue_description)
    

    # A sequence of Configurable subclasses whose config=True attributes will
    # be exposed at the command line.
    classes = List([])

    # The version string of this application.
    version = Unicode(u'0.0')

    # The log level for the application
    log_level = Enum((0,10,20,30,40,50), default_value=logging.WARN,
                     config=True,
                     help="Set the log level (0,10,20,30,40,50).")
    
    # the alias map for configurables
    aliases = Dict(dict(log_level='Application.log_level'))
    
    # flags for loading Configurables or store_const style flags
    # flags are loaded from this dict by '--key' flags
    # this must be a dict of two-tuples, the first element being the Config/dict
    # and the second being the help string for the flag
    flags = Dict()
    

    def __init__(self, **kwargs):
        SingletonConfigurable.__init__(self, **kwargs)
        # Add my class to self.classes so my attributes appear in command line
        # options.
        self.classes.insert(0, self.__class__)
        
        # ensure self.flags dict is valid
        for key,value in self.flags.iteritems():
            assert len(value) == 2, "Bad flag: %r:%s"%(key,value)
            assert isinstance(value[0], (dict, Config)), "Bad flag: %r:%s"%(key,value)
            assert isinstance(value[1], basestring), "Bad flag: %r:%s"%(key,value)
        self.init_logging()
    
    def init_logging(self):
        """Start logging for this application.

        The default is to log to stdout using a StreaHandler. The log level
        starts at loggin.WARN, but this can be adjusted by setting the 
        ``log_level`` attribute.
        """
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(self.log_level)
        self._log_handler = logging.StreamHandler()
        self._log_formatter = logging.Formatter("[%(name)s] %(message)s")
        self._log_handler.setFormatter(self._log_formatter)
        self.log.addHandler(self._log_handler)

    def _log_level_changed(self, name, old, new):
        """Adjust the log level when log_level is set."""
        self.log.setLevel(new)
    
    def print_alias_help(self):
        """print the alias part of the help"""
        if not self.aliases:
            return
            
        print "Aliases"
        print "-------"
        print self.alias_description
        print
        
        classdict = {}
        for c in self.classes:
            classdict[c.__name__] = c
        
        for alias, longname in self.aliases.iteritems():
            classname, traitname = longname.split('.',1)
            cls = classdict[classname]
            
            trait = cls.class_traits(config=True)[traitname]
            help = trait.get_metadata('help')
            print alias, "(%s)"%longname, ':', trait.__class__.__name__
            if help:
                print indent(help)
        print
    
    def print_flag_help(self):
        """print the flag part of the help"""
        if not self.flags:
            return
        
        print "Flags"
        print "-----"
        print self.flag_description
        print
        
        for m, (cfg,help) in self.flags.iteritems():
            print '--'+m
            print indent(help)
        print
    
    def print_help(self):
        """Print the help for each Configurable class in self.classes."""
        self.print_flag_help()
        self.print_alias_help()
        if self.classes:
            print "Class parameters"
            print "----------------"
            print self.keyvalue_description
            print
        
        for cls in self.classes:
            cls.class_print_help()
            print

    def print_description(self):
        """Print the application description."""
        print self.description
        print

    def print_version(self):
        """Print the version string."""
        print self.version

    def update_config(self, config):
        """Fire the traits events when the config is updated."""
        # Save a copy of the current config.
        newconfig = deepcopy(self.config)
        # Merge the new config into the current one.
        newconfig._merge(config)
        # Save the combined config as self.config, which triggers the traits
        # events.
        self.config = config

    def parse_command_line(self, argv=None):
        """Parse the command line arguments."""
        argv = sys.argv[1:] if argv is None else argv

        if '-h' in argv or '--help' in argv:
            self.print_description()
            self.print_help()
            sys.exit(1)

        if '--version' in argv:
            self.print_version()
            sys.exit(1)
        
        loader = KeyValueConfigLoader(argv=argv, aliases=self.aliases,
                                        flags=self.flags)
        config = loader.load_config()
        self.update_config(config)

    def load_config_file(self, filename, path=None):
        """Load a .py based config file by filename and path."""
        # TODO: this raises IOError if filename does not exist.
        loader = PyFileConfigLoader(filename, path=path)
        config = loader.load_config()
        self.update_config(config)

