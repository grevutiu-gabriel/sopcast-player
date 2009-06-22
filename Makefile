#!/usr/bin/make -f

NAME ?= sopcast-player
PREFIX ?= /usr
DATADIR ?= $(PREFIX)/share
INSTALLDIR ?= $(DATADIR)/$(NAME)
BINDIR ?= $(PREFIX)/bin
VLCDIR ?= vlc_python_bindings
LOCALE ?= locale
LOCALEDIR ?= $(DATADIR)/$(LOCALE)
ICONDIR ?= $(DATADIR)/icons/hicolor/scalable/apps
DESKDIR ?= $(DATADIR)/applications
INSTALL ?= install -p
EDIT ?= sed -e 's|@DATADIR@|$(DATADIR)|g' \
	    -e 's|@NAME@|$(NAME)|g' \
	    -e 's|@PYTHON@|$(PYTHON)|g' \
	    -e 's|@INSTALLDIR@|$(INSTALLDIR)|g' \
	    -e 's|@ICONDIR@|$(ICONDIR)|g' \
	    -e 's|@DESTDIR@|$(DESTDIR)|g'
PYTHON ?= $(BINDIR)/python
CFLAGS ?= -O2 -g -pipe -Wall -Wp,-D_FORTIFY_SOURCE=2 -fexceptions \
          -fstack-protector --param=ssp-buffer-size=4
VERSION ?= 0.2.0


build: language byte-compile desktop build-vlc

desktop:
	$(EDIT) $(NAME).in > $(NAME)

byte-compile:
	$(PYTHON) -c 'import compileall; compileall.compile_dir("lib", force=1)'

language:
	@echo "Generating language files..."
	@for trln in po/*.po; do \
	   lang=`basename $${trln%.*}`; \
	   mkdir -p $(LOCALE)/$$lang/LC_MESSAGES/; \
	   msgfmt $$trln -o $(LOCALE)/$$lang/LC_MESSAGES/$(NAME).mo; \
	done

build-vlc:
	cd $(VLCDIR); \
	   CFLAGS="$(CFLAGS)" $(PYTHON) -c 'import setuptools; execfile("setup.py")' build; \
	cd ..

clean:
	@for file in .pyc .py~ .so .mo .o; do \
	   echo "cleaning $$file files..." ; \
	   find . -name "*$$file" | xargs rm -f -- ; \
	done
	rm -fr $(LOCALE) || :
	rm -fr $(VLCDIR)/build || :
	rm -f $(NAME) || :

install-vlc:
	$(INSTALL) -dm 0755 $(DESTDIR)$(INSTALLDIR)/lib
	$(INSTALL) -m 0755 $(VLCDIR)/build/*/vlc.so $(DESTDIR)$(INSTALLDIR)/lib

install: install-vlc
	$(INSTALL) -dm 0755 $(DESTDIR)$(INSTALLDIR)/lib
	$(INSTALL) -dm 0755 $(DESTDIR)$(INSTALLDIR)/ui
	$(INSTALL) -dm 0755 $(DESTDIR)$(BINDIR)
	$(INSTALL) -dm 0755 $(DESTDIR)$(LOCALEDIR)
	$(INSTALL) -dm 0755 $(DESTDIR)$(ICONDIR)
	$(INSTALL) -dm 0755 $(DESTDIR)$(DESKDIR)
	$(INSTALL) -m 0644 lib/* $(DESTDIR)$(INSTALLDIR)/lib
	$(INSTALL) -m 0644 ui/* $(DESTDIR)$(INSTALLDIR)/ui
	$(INSTALL) -m 0755 $(NAME) $(DESTDIR)$(BINDIR)
	@for trln in $(LOCALE)/* ; do \
	   lang=`basename $$trln` ; \
	   $(INSTALL) -dm 0755 $(DESTDIR)$(LOCALEDIR)/$$lang/LC_MESSAGES ; \
	   $(INSTALL) -m 0644 $(LOCALE)/$$lang/LC_MESSAGES/* $(DESTDIR)$(LOCALEDIR)/$$lang/LC_MESSAGES ; \
	done
	$(INSTALL) -m 0644 $(NAME).desktop $(DESTDIR)$(DESKDIR)
	$(INSTALL) -m 0644 $(NAME).svg $(DESTDIR)$(ICONDIR)

uninstall:
	rm -fr $(DESTDIR)$(INSTALLDIR)
	rm $(DESTDIR)$(BINDIR)/$(NAME)
	rm $(DESTDIR)$(LOCALEDIR)/*/LC_MESSAGES/$(NAME).mo
	rm $(DESTDIR)$(DESKDIR)/$(NAME).desktop
	rm $(DESTDIR)$(ICONDIR)/$(NAME).svg
