#!/bin/bash

# Create volume directories
for i in {1..9}; do
    dir="volume$i"
    if [ ! -d "./volumes/$dir" ]; then
        mkdir -p "./volumes/$dir"
    fi
done

ln -srf ./chapters/{1..64}-* ./volumes/volume1/
ln -srf ./chapters/{65..121}-* ./volumes/volume2/
ln -srf ./chapters/{122..173}-* ./volumes/volume3/
ln -srf ./chapters/{174..236}-* ./volumes/volume4/
ln -srf ./chapters/{237..308}-* ./volumes/volume5/
ln -srf ./chapters/{309..385}-* ./volumes/volume6/
ln -srf ./chapters/{386..480}-* ./volumes/volume7/
ln -srf ./chapters/{481..587}-* ./volumes/volume8/
ln -srf ./chapters/{588..597}-* ./volumes/volume9/
