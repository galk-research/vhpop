TIMEOUT=600


export # This makes all variables defined here global for sub-makes

TOPTARGETS := all clean superclean zip archive
SUBDIRS := $(wildcard */)

$(TOPTARGETS): $(SUBDIRS)

$(SUBDIRS):
	@echo "Now working on problems in " $@
	cd $@ && make -f ../Makefile.subdir $(MAKECMDGOALS)
	# $(MAKE) -C $@ $(MAKECMDGOALS)

.PHONY: $(TOPTARGETS) $(SUBDIRS)


# see also: https://stackoverflow.com/questions/9249757/recursive-make-in-subdirectories



