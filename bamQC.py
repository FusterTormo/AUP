#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
MAIN: Comprobar la calidad del alineamiento
"""

import os
import subprocess
import sys

import getCommands as gc
import constantes as cte

# Constantes locales
bed = "alignment/{}".format(cte.bedoutput)
bam = "alignment/{}".format(cte.finalbam)
fastqc = cte.fastqcdir
fastqcFI = "fastqc_data.txt"

def convertirManifest(manifest) :
    """
    Convierte el manifest en un diccionario

    Abre el archivo manifest y convierte todas las regiones en un diccionario con el formato: {"chr" : [[ini_reg1 - fin_reg1], [ini_reg2 - fin_reg2]]}

    Returns
    -------
        dict
            El manifest convertido en diccionario
    """
    m = {}
    with open(manifest, "r") as fi :
        for l in fi :
            aux = l.split("\t")
            chr = aux[0]
            ini = int(aux[1])
            fin = int(aux[2])
            if chr in m.keys() :
                m[chr].append([ini, fin])
            else :
                m[chr] = [[ini, fin]]
    return m

def enManifest(read, manifest) :
    """
    Comprueba si un read pasado por parametro esta dentro del manifest o no

    Se comprueba si, al menos, una parte del read esta dentro de las regiones del manifest.

    Parameters
    ----------
        read : str
            Cadena de texto con el formato cromosoma\tinicio\tfin
        manifest : dict
            Diccioario en el que buscar si el read esta dentro o no

    Returns
    -------
        bool
            True si el read esta dentro del manifest. False en caso contrario
    """
    esta = False
    aux = read.split("\t")
    chr = aux[0]
    ini = int(aux[1])
    fin = int(aux[2])
    if chr in manifest.keys() :
        for r in manifest[chr] :
            if fin >= r[0] and ini <= r[1] :
                esta = True
                break
    return esta

def main(manifest = cte.manifest, imprimir = False) :
    """
    Programa principal

    Recoge los datos de calidad del bam. Se consideran parametros de calidad el numero de reads que se tenian al principio. El numero de reads que contiene el bam. El numero de reads que estan dentro
    del manifest (ON target) y el numero de reads fuera del manifest (OFF target). Un read se considera ON target si tiene, al menos, una base dentro de las regiones definidas por el manifest.
    Se guardan todos los datos de calidad en un archivo de texto llamado alnQC.txt
    """
    on = 0
    off = 0
    fqreads = 0
    bamreads = 0
    reads = []

    # Buscar los archivos necesarios para poder crear el control de calidad: la carpeta con la salida de FASTQC, el  archivo bed (o en su defecto el bam con el que crear el bed) y el manifest
    if not os.path.isdir(fastqc) :
        if not os.path.isfile(bed) and not os.path.isfile(bam) :
            print("ERROR: No se han encontrado los archivos necesarios para poder ejecutar el control de calidad")
            sys.exit()

    if not os.path.isfile(manifest) :
        print("ERROR: Manifest no encontrado en ruta {}".format(manifest))
        sys.exit()

    # Comprobar si existe la carpeta de FASTQC. Extraer la informacion necesaria de los FASTQ en tal caso
    print("INFO: Leyendo FASTQ ({})".format(fastqc))
    if os.path.isdir(fastqc) :
        for dir, dirnames, filenames in os.walk(fastqc) :
            break

        for d in dirnames :
            with open("{}/{}/{}".format(fastqc, d, fastqcFI), "r")  as fi :
                for l in fi :
                    if l.startswith("Total Sequences") :
                        reads.append(int(l.split("\t")[-1].strip()))
                        break

    # Comprobar si existe el manifest. Convertirlo en un diccionario para acceder a los reads mas rapidamente
    print("INFO: Leyendo manifest ({})".format(manifest))
    if os.path.isfile(manifest) :
        dic = convertirManifest(manifest)
        print("INFO: Leyendo alineamiento ({})".format(bed))
        if not os.path.isfile(bed) :
            print("INFO: Creando archivo bed con las coordenadas del bam")
            proc = subprocess.Popen(gc.getBam2bed(bam, bed), shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            out, err = proc.communicate()
        if os.path.isfile(bed) :
            with open(bed, "r") as fi :
                for l in fi :
                    if enManifest(l, dic) :
                        on += 1
                    else :
                        off += 1

    if reads == 0 and on == 0 and off == 0 :
        print("ERROR: No hay datos para poder crear el archivo de calidad del bam")
    else :
        fqreads = sum(reads)
        breads = on + off
        if imprimir :
            print("Reads en FASTQ: {}".format(fqreads))
            print("Reads en BAM: {}".format(breads))
            print("Reads ON target: {} ({:.2f} %)".format(on, 100*on/breads))
            print("Reads OFF target: {} ({:.2f} %)".format(off, 100*off/breads))
        else :
            print("INFO: Escribiendo resultados en {}".format(cte.qcaln))
            with open(cte.qcaln, "w") as fi :
                fi.write("{")
                fi.write("\'FASTQ\': {},".format(fqreads))
                fi.write("\'BAM': {},".format(breads))
                fi.write("\'ON\': {},".format(on))
                fi.write("\'OFF\': {}".format(off))
                fi.write("}")

if __name__ == "__main__" :
    """
        USO: ./bamQC.py [input.bam] [manifest.bed]
    """
    if len(sys.argv) > 1 :
        bam = sys.argv[1]
        if len(sys.argv) >= 3 :
            mani = sys.argv[2]
            main(mani, True) # Hacer el control de calidad con un bam y un manifest predeterminado
        else :
            main(imprimir = True) # Hacer el control de calidad con un bam determinado
    else :
        main() # El programa supone que se ha invocado dentro de una carpeta de analisis, donde existe una carpeta alignment con los bams y una carpeta fastqc con los datos de calidad del FASTQ
