#!/bin/bash
# takes a list of file URLs and creates the similar folder structure locally and downloads those files
# make sure your provided path has a trailing /

SPATH=$1

if [ ! "$SPATH" ]; then
	echo "You must provide the save path"
	exit 0
fi

if [ ! -d "$SPATH" ]; then
	echo "'$SPATH' does not exist"
	exit 0
fi

FILE=/client/files.txt

if [ ! -f "$FILE" ]; then
	echo "'/client/files.txt' file missing"
	exit 0
fi

while read -r line
do
	hst="$line"
	clean=$(echo -n "$hst" | sed 's/http[s]\?:\/\///g' | sed -E 's/(.*)\/.*/\1 /')
	NPATH="$SPATH/$clean"
	if [ ! -d "$NPTH" ]; then
		mkdir -p $NPATH
	fi
	echo "Getting: $line"
	wget -q --directory-prefix="$NPATH" "$line"
done < "$FILE"
