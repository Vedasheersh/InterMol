import subprocess
from collections import OrderedDict
import sys
import os
import pdb

import intermol.unit as units

def gromacs_energies(top=None, gro=None, mdp=None, gropath='',grosuff='', grompp_check=False):
    """

    gropath = path to gromacs binaries
    grosuff = suffix of gromacs binaries, usually '' or '_d'

    """
    directory, _ = os.path.split(top)

    tpr  = os.path.join(directory , 'topol.tpr')
    ener  = os.path.join(directory , 'ener.edr')
    ener_xvg  = os.path.join(directory , 'energy.xvg')
    conf  = os.path.join(directory , 'confout.gro')
    mdout = os.path.join(directory , 'mdout.mdp')
    state  = os.path.join(directory , 'state.cpt')
    traj  = os.path.join(directory , 'traj.trr')
    log  = os.path.join(directory , 'md.log')
    stdout = os.path.join(directory, 'gromacs_stdout.txt')
    stderr = os.path.join(directory, 'gromacs_stderr.txt')

    grompp_bin = os.path.join(gropath, 'grompp' + grosuff)
    mdrun_bin = os.path.join(gropath, 'mdrun' + grosuff)
    genergy_bin = os.path.join(gropath, 'g_energy' + grosuff)

    # grompp'n it up
    cmd = [grompp_bin, '-f', mdp, '-c', gro, '-p', top, '-o', tpr, '-po', mdout, '-maxwarn', '1']
    print 'Running GROMACS with command:'
    print ' '.join(cmd)
    with open(stdout, 'w') as out, open(stderr, 'w') as err:
        exit = subprocess.call(cmd, stdout=out, stderr=err)
    if exit:
        raise Exception('grompp failed for {0}'.format(top))
    elif grompp_check:
        return

    # mdrunin'
    cmd = [mdrun_bin, '-nt', '1', '-s', tpr, '-o', traj, '-cpo', state, '-c', 
        conf, '-e', ener, '-g', log]
    print 'Running GROMACS with command:'
    print ' '.join(cmd)
    with open(stdout, 'wa') as out, open(stderr, 'wa') as err:
        exit = subprocess.call(cmd, stdout=out, stderr=err)
    if exit:
        raise Exception('mdrun failed for {0}'.format(top))

    # energizin'
    select = " ".join(map(str, range(1, 20))) + " 0 "
    cmd = 'echo {select} | {genergy_bin} -f {ener} -o {ener_xvg} -dp'.format(
            select=select, genergy_bin=genergy_bin, ener=ener, ener_xvg=ener_xvg)
    print 'Running GROMACS with command:'
    print cmd
    with open(stdout, 'wa') as out, open(stderr, 'wa') as err:
        exit = subprocess.call(cmd, stdout=out, stderr=err, shell=True)
    if exit:
        raise Exception('g_energy failed for {0}'.format(top))

    # extract g_energy output and parse initial energies
    with open(ener_xvg) as f:
        all_lines = f.readlines()

    types = []
    for line in all_lines:
        if line[:3] == '@ s':
            types.append(line.split('"')[1])

    # take last line
    data = map(float, all_lines[-1].split()[1:])  # [0] is the time

    # give everything units
    data = [value * units.kilojoules_per_mole for value in data]

    # pack it up in a dictionary
    e_out = OrderedDict(zip(types, data))

    # discard non-energy terms
    unwanted = ['Kinetic En.', 'Total Energy', 'Temperature', 'Pressure',
            'Volume', 'Box-X', 'Box-Y', 'Box-Z', 'Pres. DC']
    for group in unwanted:
        if group in e_out:
            del e_out[group]

    # dispersive energies - do buckingham energies also get dumped here?
    dispersive = ['LJ (SR)', 'LJ-14', 'Disper.corr.']
    e_out['Dispersive'] = 0 * units.kilojoules_per_mole
    for group in dispersive:
        if group in e_out:
            e_out['Dispersive'] += e_out[group]

    # electrostatic energies
    electrostatic = ['Coulomb (SR)', 'Coulomb-14', 'Coul. recip.']
    e_out['Electrostatic'] = 0 * units.kilojoules_per_mole
    for group in electrostatic:
        if group in e_out:
            e_out['Electrostatic'] += e_out[group]

    e_out['Non-bonded'] = e_out['Electrostatic'] + e_out['Dispersive']

    # all the various dihedral energies - what else goes in here?
    all_dihedrals = ['Ryckaert-Bell.', 'Proper Dih.', 'Improper Dih.']
    e_out['All dihedrals'] = 0 * units.kilojoules_per_mole
    for group in all_dihedrals:
        if group in e_out:
            e_out['All dihedrals'] += e_out[group]

    return e_out, ener_xvg
