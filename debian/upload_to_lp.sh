#!/bin/bash

distros='
intrepid
jaunty
karmic
lucid
maverick
natty
oneiric
'

if [[ -n `cat 'changelog' | grep -E '~ppa[0-9]*~(hardy|intrepid|jaunty|karmic|lucid|maverick|natty|oneiric)[0-9]*'` ]]
then
	for replacement_distro in ${distros};
	do
		for cur_distro in ${distros};
		do		
			if [ ${cur_distro} != ${replacement_distro} ]
			then
				while [[ -n `cat 'changelog' | awk 'NR < 2' | grep ${cur_distro}` ]]
				do
					sed -i "0,/${cur_distro}/s//${replacement_distro}/" 'changelog'


				
				done
			fi
		done
		debuild -S -sa
		wait
		dput my-ppa '../../'`cat 'changelog' | awk 'NR < 2' | sed 's/ (/_/g' | sed 's/).*/_source.changes/g'`
		
	done
	
	echo 'Cleaning up...'
	rm -rf ../../*.dsc ../../*.changes ../../*.tar.gz ../../*.build ../../*.upload
else
	echo 'Error in the format of the chanelog file!'
	echo 'Package must be in the form of <pacakge name> (<version>~ppa<[0-9]*>~<release><[0-9]*>).'
fi


