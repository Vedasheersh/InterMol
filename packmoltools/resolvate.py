#!/usr/bin/python

#=============================================================================================
# resolvate
#
# Resolvate a PDB file and produce an AMBER .crd file.
#=============================================================================================
# AUTHORS
#
# Written by John Chodera, Stanford University, 2007-03-05
#=============================================================================================
# REQUIREMENTS
# - Packmol: http://www.ime.unicamp.br/~martinez/packmol/
# - numarray
#=============================================================================================
# TODO
#=============================================================================================
# VERSION CONTROL INFORMATION
__version__ = "$Revision: $"                                                                                              
#=============================================================================================
# IMPORTS
import sys
import os.path
from optparse import OptionParser # For parsing of command line arguments
import commands
import shutil
#=============================================================================================

#=============================================================================================
# PARAMETERS
#=============================================================================================
packmol = '${HOME}/local/src/packmol/src/packmol'

#=============================================================================================
# SUBROUTINES
#=============================================================================================
def getPresentSequence(pdbfilename, chain=' '):
    """Extract the sequence for which there are atomic coordiantes defined from a PDB file.

    present_sequence = getPresentSequence(pdbfilename, chain=' ')
    
    REQUIRED ARGUMENTS
      pdbfilename - the filename of the PDB file to import from

    OPTIONAL ARGUMENTS
      chain - the one-character chain ID of the chain to import (default ' ')

    RETURN VALUES
      sequence - array of residue names

    The ATOM records are read, and the sequence for which there are atomic coordinates is stored.

    """

    # Read the PDB file into memory.
    pdbfile = open(pdbfilename, 'r')
    lines = pdbfile.readlines()
    pdbfile.close()

    # Extract the sequence for which there are defined atomic coordinates.
    sequence = [ ]
    last_resSeq = None
    for line in lines:
      if line[0:6] == "ATOM  ":
        # Parse line into fields.
        field = { }
        field["serial"] = int(line[6:11])
        field["name"] = line[12:16]
        field["altLoc"] = line[16:17]
        field["resName"] = line[17:20]
        field["chainID"] = line[21:22]
        field["resSeq"] = int(line[22:26])
        field["iCode"] = line[26:27]
        
        # Add these residues to the sequence if they below to the chain of interest.
        if (chain == field['chainID']):
          if(field["resSeq"] != last_resSeq):
            sequence.append(field["resName"])
            last_resSeq = field["resSeq"]

    # Return dictionary of present residues.
    return sequence

def readAtomsFromPDB(pdbfilename):
    """Read atom records from the PDB and return them in a list.

    present_sequence = getPresentSequence(pdbfilename, chain=' ')
    
    REQUIRED ARGUMENTS
      pdbfilename - the filename of the PDB file to import from

    OPTIONAL ARGUMENTS
      chain - the one-character chain ID of the chain to import (default ' ')

    RETURN VALUES
      sequence (dictionary) - sequence[residue_id] is the one-letter code corresponding to residue index residue_id

    The ATOM records are read, and the sequence for which there are atomic coordinates is stored.

    """

    # Read the PDB file into memory.
    pdbfile = open(pdbfilename, 'r')
    lines = pdbfile.readlines()
    pdbfile.close()

    # Read atoms.
    atoms = [ ]
    for line in lines:
        if line[0:6] == "ATOM  ":
            # Parse line into fields.
            atom = { }
            atom["serial"] = int(line[6:11])
            atom["name"] = line[12:16]
            atom["altLoc"] = line[16:17]
            atom["resName"] = line[17:20]
            atom["chainID"] = line[21:22]
            atom["resSeq"] = int(line[22:26])
            atom["iCode"] = line[26:27]
            atom["x"] = float(line[30:38])
            atom["y"] = float(line[38:46])
            atom["z"] = float(line[46:54])

            atom["occupancy"] = 1.0
            if (line[54:60].strip() != ''):
              atom["occupancy"] = float(line[54:60])
              
            atom["tempFactor"] = 0.0
            if (line[60:66].strip() != ''):
              atom["tempFactor"] = float(line[60:66])
            
            atom["segID"] = line[72:76]
            atom["element"] = line[76:78]
            atom["charge"] = line[78:80]
            
            atoms.append(atom)
            
    # Return list of atoms.
    return atoms

def writeAtomsToPDB(pdbfilename, atoms, renumber = False):
  """Write atom records to PDB file.

  REQUIRED ARGUMENTS
    pdbfilename - the name of the PDB file to write
    atoms - a list of atom dictionaries -- see readAtomsFromPdb

  OPTIONAL ARGUMENTS
    if renumber is True, then the atom and residue numbers will be renumbered starting with 1

  RETURN VALUES
    none

  EXAMPLE
  writeAtomsToPdb(pdbfilename, atoms)
  
  """

  # Renumber if desired.
  if (renumber):
    first_residue = atoms[0]["resSeq"]
    serial = 1
    resSeq = 0
    last_resSeq = None
    for atom in atoms:
      atom["serial"] = serial
      serial += 1

      if(atom["resSeq"] != last_resSeq):
        resSeq += 1
        last_resSeq = atom["resSeq"]
      atom["resSeq"] = resSeq      
      
  # Read the PDB file into memory.
  pdbfile = open(pdbfilename, 'w')
  
  # Write atoms.
  for atom in atoms:
    pdbfile.write('ATOM  %(serial)5d %(name)4s%(altLoc)c%(resName)3s %(chainID)c%(resSeq)4d%(iCode)c   %(x)8.3f%(y)8.3f%(z)8.3f%(occupancy)6.2f%(tempFactor)6.2f%(element)2s%(charge)2s\n' % atom)

  pdbfile.close()


def readAmberCrd(crd_filename):
  """Read an AMBER format .crd file.

  REQUIRED ARGUMENTS
    crd_filename - name of AMBER .crd file to read

  RETURNS
    title - title string
    natoms - number of atoms
    coordinates - 3*natoms array of coordinates
    box_dimensions - box coordinates if present, or None if not
    box_angles - box angles if present, or None if not    
  
  EXAMPLE
    crd_filename = 'output.crd'
    (title, natoms, coordinates, box_dimensions, box_angles) = readAmberCrd(crd_filename)

  """
  
  # Read contents of file.
  infile = open(crd_filename, 'r')
  lines = infile.readlines()
  infile.close()

  # Parse header.
  title = lines.pop(0).rstrip(' \n')
  natoms = int(lines.pop(0).split()[0])

  # Parse coordinates.
  coordinates = [ ]
  for line in lines:
    elements = line.split()
    for element in elements:
      coordinates.append(float(element))

  # Extract box dimensions and coordinates, if present.
  if (len(coordinates) >= 3*natoms + 3):
    box_dimensions = coordinates[3*natoms:3*natoms+3]
  if (len(coordinates) == 3*natoms + 6):
    box_angles = coordinates[3*natoms+3:3*natoms+6]
  coordinates = coordinates[0:3*natoms]

  # Return results
  return (title, natoms, coordinates, box_dimensions, box_angles)  

def writeAmberCrd(crd_filename, coordinates, title = '', box_dimensions = None, box_angles = None):
  """Write an AMBER format .crd file.
  
  REQUIRED ARGUMENTS
    crd_filename - the filename of the AMBER .crd file to be written
    coordinates - array or list of length 3*Natoms of atomic coordinates
    box_coordinates - box coordinates to be appended to end

  RETURNS
    none

  EXAMPLE
    crd_filename = 'output.crd'
    coordinates = [1.0, 2.0, 3.0]
    writeAmberCrd(crd_filename, natoms, coordinates)  
    
  """
  # Check to make sure number of coordinates is divisiable by 3.
  if(len(coordinates) % 3 != 0):
    raise ParameterError('Number of atomic cordinates is not a multiple of 3.')
  
  # Determine number of atoms.
  natoms = len(coordinates) / 3
  
  # Append box_coordinates.
  coordinates_to_write = coordinates
  if (box_dimensions):
    coordinates_to_write += box_dimensions
  if (box_angles):
    coordinates_to_write += box_angles
      
  # Open file to write.
  outfile = open(crd_filename, 'w')
  
  # Write header.
  outfile.write('%s\n' % title)
  outfile.write('%6d\n' % natoms)
  
  # Write coordinates.
  coordinates_this_line = 0
  for coordinate in coordinates_to_write:
    # Write a coordinate.
    outfile.write('%12.7f' % coordinate)
    coordinates_this_line += 1
    
    # Wrap if we have written 6 coordinates/line.
    if (coordinates_this_line == 6):
      outfile.write('\n')
      coordinates_this_line = 0

  outfile.close()
  return

#=============================================================================================
# MAIN
#=============================================================================================
# Create command-line argument options.
usage_string = """
Resolvate a given PDB file to produce a solvated AMBER .crd file.
Numbers of water molecules are determined from reference PDB file, and box volume from reference AMBER .crd file.

usage: %prog --refpdb REFERENCE.pdb --refcrd REFERENCE.crd --source SOURCE.pdb --output OUTPUT.crd

example: %prog --refpdb system.pdb --refcrd system.crd --source extracted.pdb --output resolvated.crd
"""

version_string = "%prog %__version__"

parser = OptionParser(usage=usage_string, version=version_string)

parser.add_option("-p", "--refpdb", metavar='REFERENCE.pdb',
                  action="store", type="string", dest='reference_pdb', default=None,
                  help="Reference PDB file (to determine number of waters).")
parser.add_option("-c", "--refcrd", metavar='REFERENCE.crd',
                  action="store", type="string", dest='reference_crd', default=None,
                  help="Reference AMBER .crd file (to determine box dimensions).")
parser.add_option("-s", "--source", metavar='SOURCE.pdb',
                  action="store", type="string", dest='source_pdb', default=None,
                  help="PDB file to resolvate.")
parser.add_option("-o", "--output", metavar='OUTPUT.crd',
                  action="store", type="string", dest='output_crd', default=None,
                  help="Name of solvated AMBER .crd file to generate.")

# Parse command-line arguments.
(options,args) = parser.parse_args()

# Perform minimal error checking.
if ((not options.reference_pdb) or (not options.reference_crd) or (not options.source_pdb) or (not options.output_crd)):
  parser.print_help()
  parser.error("All options must be specified.\n")

reference_pdb = options.reference_pdb
reference_crd = options.reference_crd
source_pdb = options.source_pdb
output_crd = options.output_crd

# Create temporary directory.
import tempfile
import os.path
tmpdir = tempfile.mkdtemp()
print "tmpdir is %s" % tmpdir

# Extract sequence from reference PDB file.
reference_sequence = getPresentSequence(reference_pdb)

# Extract seqence from source PDB file.
source_sequence = getPresentSequence(source_pdb)

# Determine number of water molecules as difference in sequence lengths.
nwat = len(reference_sequence) - len(source_sequence)
print "Will add %d water molecules." % nwat

# Extract box coordinates.
(title, natoms, coordinates, box_dimensions, box_angles) = readAmberCrd(reference_crd)
      
# Compute box parameters.
(box_x, box_y, box_z) = box_dimensions
(center_x, center_y, center_z) = (box_x/2.0, box_y/2.0, box_z/2.0)

# Get date.
date = commands.getoutput('date')

# Temporary output PDB filename.
output_pdb = os.path.join(tmpdir, 'output.pdb')

# Generate water reference file from atoms in first non-solute residue in reference PDB file.
atoms = readAtomsFromPDB(reference_pdb)
reference_water_residue_atoms = []
first_water_residue = len(source_sequence) + 1
for atom in atoms:
  if (atom['resSeq'] == first_water_residue):
    reference_water_residue_atoms.append(atom)
reference_water_pdb = os.path.join(tmpdir, 'wat.pdb')
writeAtomsToPDB(reference_water_pdb, reference_water_residue_atoms, renumber=True)

# Copy source PDB file.
shutil.copy(source_pdb, os.path.join(tmpdir, 'source.pdb'))

# Generate title.
title = "Resolvation of %(source_pdb)s in %(box_x)f A x %(box_y)f A x %(box_z)f A box by %(nwat)d water molecules" % vars()

# Construct Packmol input file.
packmol_input_filename = os.path.join(tmpdir, 'packmol.in')
packmol_input = """\
#
# Generated by resolvate.py on %(date)s
# %(title)s
#

# All atoms from diferent molecules will be at least 'tolerance' A apart at the solution

tolerance 2.0

# The type of the files will be pdb 

filetype pdb

# The name of the output file

output output.pdb

# The protein will be fixed with its center of mass at center of the
# box, and no rotation (the first three zeros correspond to the position
# of the center of mass and the last three correspond to the euler
# angles of rotation, in radian, relative to the position in the input
# file). 

structure source.pdb
  number 1 
  resnumbers 1
  fixed %(center_x)f %(center_y)f %(center_z)f 0. 0. 0.
  centerofmass
end structure

# Water molecules will be put inside a box that contains the protein and ions.
structure wat.pdb
  number %(nwat)d
  resnumbers 0
  inside box 0.0 0.0 0.0 %(box_x)f %(box_y)f %(box_z)f
end structure

""" % vars()

outfile = open(packmol_input_filename, 'w')
outfile.write(packmol_input)
outfile.close()

# Execute Packmol.
print "Running packmol..."
command = 'cd %(tmpdir)s ; %(packmol)s < %(packmol_input_filename)s' % vars()
output = commands.getoutput(command)
print output

# Read the output PDB file.
atoms = readAtomsFromPDB(os.path.join(tmpdir, 'output.pdb'))

# Clean up temporary directory.
for filename in os.listdir(tmpdir):
  os.remove(os.path.join(tmpdir,filename))
os.rmdir(tmpdir)

# Get solvent coordinates (chain A) and solute coordinates (chain B)
solvent_coordinates = []
solute_coordinates = []

for atom in atoms:
  # Solvent.
  if (atom['chainID'] == 'A'):
    solvent_coordinates += [ atom['x'], atom['y'], atom['z'] ]
  # Solute.
  if (atom['chainID'] == 'B'):
    solute_coordinates += [ atom['x'], atom['y'], atom['z'] ]

# Write coordinates.
coordinates = solute_coordinates + solvent_coordinates
writeAmberCrd(output_crd, coordinates, title = title, box_dimensions = box_dimensions, box_angles = box_angles)

  

