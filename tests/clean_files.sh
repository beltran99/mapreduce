#!/bin/bash

directory="data/map"
if [ -n "$(ls -A $directory)" ]; then
    rm $directory/*
fi

directory="data/reduce"
if [ -n "$(ls -A $directory)" ]; then
    rm $directory/*
fi