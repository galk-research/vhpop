TIMEOUT = 600
LANDMARK_SCRIPT = /home/neria/MODDED_FD/fast-downward.py
DATADIR = /data/neria

export # This makes all variables defined here global for sub-makes

TOPTARGETS := all clean superclean zip archive
SUBDIRS := $(wildcard */)

# The directory where this Makefile is located
THIS_DIR := $(patsubst %/,%,$(dir $(abspath $(firstword $(MAKEFILE_LIST)))))

$(TOPTARGETS): $(SUBDIRS)

$(SUBDIRS):
	@echo "Now working on problems in " $@
	@cd $@ && $(MAKE) -f $(THIS_DIR)/Makefile.subdir $(MAKECMDGOALS)
	# $(MAKE) -C $@ $(MAKECMDGOALS)

.PHONY: $(TOPTARGETS) $(SUBDIRS)


# see also: https://stackoverflow.com/questions/9249757/recursive-make-in-subdirectories



