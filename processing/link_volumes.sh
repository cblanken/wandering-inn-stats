#!/bin/bash

# Create volume directories
for i in {1..9}; do
    dir="volume$i"
    if [ ! -d "./volumes/$dir" ]; then
        mkdir -p "./volumes/$dir"
    fi
done

latest_chapter=$(ls ./chapters/text/ | wc -l)

function link {
    vol_name=$1
    start=$2
    end=$3
    for i in $(seq $start $end); do
        ln -srf ./chapters/text/$i-* ./volumes/$vol_name/
    done
}

link "volume1" 1 64
link "volume2" 65 121
link "volume3" 122 173
link "volume4" 174 236
link "volume5" 237 308
link "volume6" 309 385
link "volume7" 386 480
link "volume8" 481 587
link "volume9" 588 $latest_chapter
