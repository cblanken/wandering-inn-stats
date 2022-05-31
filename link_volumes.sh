#!/bin/bash

# Create volume directories
for i in {1..8}; do
    dir="volume$i"
    if [ ! -d "./volumes/$dir" ]; then
        mkdir -p "./volumes/$dir"
    fi
done

ln -sr ./chapters/{1..64}-* ./volumes/volume1/
ln -sr ./chapters/{65..121}-* ./volumes/volume2/
ln -sr ./chapters/{122..173}-* ./volumes/volume3/
ln -sr ./chapters/{174..236}-* ./volumes/volume4/
ln -sr ./chapters/{237..308}-* ./volumes/volume5/
ln -sr ./chapters/{309..385}-* ./volumes/volume6/
ln -sr ./chapters/{386..480}-* ./volumes/volume7/
ln -sr ./chapters/{481..585}-* ./volumes/volume8/
