#!/usr/bin/env python
# coding: utf-8

"""

Automatical reprocessing .fg5 projects

Aleksei Polukhin
Department of Gravimetry and Geodynamics
Center of Geodesy, Cartography and SDI (TsNIIGAiK)
Mon Jan 23 15:10:50 2017

"""

from ldtp import *
import zeep
from astropy.time import Time
import sys
from os import remove, path, getcwd, system
from subprocess import Popen
from shutil import copyfile
from struct import unpack_from
import numpy as np
from re import finditer
from prettytable import PrettyTable

def get_datetime(filename):
    # Reading binary data
    with open(filename, "rb") as f:
        bin_data = f.read()

    # Searching datetime start byte
    date_key = r'\xe0.\x00\x00\x0b'
    matches = []
    for match in finditer(date_key, bin_data):
        matches.append(match.span())
    date_offset = matches[-1][0] - 8
    
    # Unpacking datetime
    time_values = {}
    hours, days = unpack_from("<II", bin_data, date_offset)
    secs = days * 45.0 * 60.0 + hours / (4294967295.0/45.0) * 60.0
    time_values["UNIX"] = secs - 2938117104000.0

    # Convert to ISO and MJD time formats
    t = Time(time_values["UNIX"], format="unix")
    t.format = "iso"
    t.out_subfmt = "date_hm"
    time_values["ISO"] = t.value
    t.format = "mjd"
    time_values["MJD"] = str(int(np.floor(t.value)))

    return time_values

def get_nsets(filename):
    # Reading binary data
    with open(filename, "rb") as f:
        bin_data = f.read()
        
    masks = {
        "project": r'\x24\x40\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00',
        "fact": r'\xF4\xBF\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    }
    n_sets = {}
    # Searching datetime start byte
    for name, mask in masks.iteritems(): 
        matches = []
        for match in finditer(mask, bin_data):
            matches.append(match.span())
        date_offset = matches[-1][1]
        n = unpack_from("<h", bin_data, date_offset)
        n_sets[name] = int(n[0])
    
    return n_sets

def pole_coords(mjd):  
    # Get values of pole coords from IERS
    try:
        client = zeep.Client("https://data.iers.org/eris/webservice/eop/eop.wsdl")
    except:
        print("No connection to Internet. Leaving with initial Pole coords")
        return -1
    get_eop = lambda bulletin: {pole: client.service.readEOP(pole, bulletin, mjd) for pole in ["x_pole", "y_pole"]}
    bltn = "EOP 14 C04 (IAU2000)"
    eop_values = get_eop(bltn)
    if eop_values["x_pole"] == None and eop_values["y_pole"] == None:
        print("Values for MJD %s not found in EOP 14 C04 (IAU2000). Taking values from Bulletin A..." % mjd)
        bltn = "Bulletin A"
        eop_values = get_eop(bltn)
    eop_values = {pole:str(round(float(eop_values[pole]) / 1000, 4)) for pole in ["x_pole", "y_pole"]}
    eop_values["BULLETIN"] = bltn
    
    return eop_values

def get_buttons(window):
    objects = getobjectlist(window)
    tbar_idx = objects.index("tbar0")
    buttons = objects[tbar_idx + 5 : tbar_idx + 8]
    buttons.append(objects[tbar_idx + 11])
    return buttons

def g9_proc(filename, vgrad):
    
    g9_bin = r"C:\Program Files\Micro-g LaCoste Inc\bin\g9.exe"
    if not path.isfile(g9_bin):
        g9_bin = r"C:\Program Files (x86)\Micro-g LaCoste Inc\bin\g9.exe"
   
    system("TASKKILL /F /IM g9.exe")
    Popen("%s %s" % (g9_bin, filename))
    
    wdw = "*Micro-g*"
    results = {}

    frmSetup = 'frmSetup'
    frmETGTABSetup = 'frmETGTABSetup'
    frmOceanLoad = 'frmOceanLoad'
    btnSetupOk = u'btn\u041e\u041a'
    frmOverrideDialog = 'frmOverrideDialog'
    
    """
    frmSetup = "dlgSetup"
    frmETGTABSetup = 'dlgETGTABSetup'
    frmOceanLoad = 'dlgOceanLoad'
    btnSetupOk = 'btnOK'
    frmOverrideDialog = 'dlgOverrideDialog'
    """

    wait(1)

    btnSetup, btnGo, btnStop, btnAbout = get_buttons(wdw)
    
    click(wdw, btnSetup) 
    wait(1)
    
    # Information Tab
    #     Get Site Name and Code
    results["name"] = gettextvalue(frmSetup, 'txt0')
    results["code"] = gettextvalue(frmSetup, 'txt1')
    
    #     Get Setup Height
    results["h_setup"] = float(gettextvalue(frmSetup, 'txt7'))
    
    #     Set Nominal Pressure
    click(frmSetup, "btnSet")
    
    #     Set Gradient
    settextvalue(frmSetup, 'txt6', str(vgrad))
    
    #     Get Project Start DateTime
    project_datetime = get_datetime(filename)
    results["iso"] = project_datetime["ISO"]
    results["mjd"] = project_datetime["MJD"]
    
    #     Get Polar X/Y from IERS and set
    eop_data = pole_coords(project_datetime["MJD"])
    if eop_data == -1:
        results["bltn"] = "Default"
        
    else:
        settextvalue(frmSetup, 'txt8', eop_data["x_pole"])
        settextvalue(frmSetup, 'txt9', eop_data["y_pole"])
        results["bltn"] = eop_data["BULLETIN"]
    
    #     Set Transfer Height
    settextvalue(frmSetup, 'txt10', "130")
    
    # Acqusition Tab
    selecttab(frmSetup, 'ptl0', 'ptabAcquisition')
    #     Get Sets and Drops values
    results["sets"] = get_nsets(filename)["fact"]
    results["drops"] = gettextvalue(frmSetup, 'txt1')
    
    # Control Tab
    selecttab(frmSetup, 'ptl0', 'ptabControl')
    #     Calculate Tidal Corrections
    comboselect(frmSetup, 'cbo1', "ETGTAB")
    click(frmSetup, 'btnSetup1')
    click(frmETGTABSetup, 'btnRunOceanLoad')
    click(frmOceanLoad, 'btnOK')
    wait(1)
    click(frmETGTABSetup, 'btnOK')
    
    #    Uncheck box  Auto Peak Detection
    if verifycheck(frmSetup, 'chkAutoPeakDetection'):
        uncheck(frmSetup, 'chkAutoPeakDetection')
        
    # Push OK to close Setup window
    click(frmSetup, btnSetupOk)

    # Start processing
    click(wdw, btnGo)
    
    if guiexist(frmOverrideDialog):
        click(frmOverrideDialog, 'btnYes')

    # Waiting till processing ends
    wait(5)
    while int(gettextvalue('frmState', 'txt32')) != results["sets"]:
        wait(3)
    wait(5)

    results["gravity"] = float(gettextvalue('frmState', 'txt42'))
    results["sd"] = float(gettextvalue('frmState', 'txt43'))
    
    system("TASKKILL /F /IM g9.exe")

    #selectmenuitem(wdw, "mnuProject;mnuClose")
    
    return results

def az_proc(project_azumuth, h_fact, h_mod, wzz):
    # Processing gravity at effective height
    g_eff = g9_proc(project_azumuth, wzz)
    g_eff["h_eff"] = h_fact + g_eff["h_setup"] - h_mod

    with open(path.splitext(project_azumuth)[0] + ".project.txt", 'a') as f:
        f.write(('\n\nReprocessing\nMJD:  {1}\nBulletin:  {2}		\nMeasurement Start:  {0}		\nGravity at Effective Height:  {3:.2f} \xb5Gal		\nStandard Deviation:  {4:.2f} \xb5Gal		\nEffective Height:  {5:.2f} cm		\nSetup Height:  {6:.2f} cm		\nHeight_mod:  {7:.2f} cm		\nFactory Height:  {8:.2f} cm').format(g_eff["iso"], 
                g_eff["mjd"], g_eff["bltn"], g_eff["gravity"],
                g_eff["sd"], g_eff["h_eff"], g_eff["h_setup"],
                h_mod, h_fact))
    return g_eff

def main():
    h_mod = 7.08
    h_fact = 80.60
    wzz = 0.00
	
    # Process project at current directory
    project = getcwd()
    print project
	
    az_results = {}
    for az in ["north", "south"]:
        az_file = path.join(project, az, az + ".fg5")
        if path.isfile(az_file):
            az_results[az] = az_proc(az_file, h_fact, h_mod, wzz)
        else:
            print("Project file for %s azimuth not found" % az)
            continue
        
    az_results["mean"] = {}
    for key in ["gravity", "h_setup", "h_eff"]:
        az_results["mean"][key] = np.mean([az_results["north"][key], az_results["south"][key]])
    az_results["sd"] = np.sqrt(az_results["north"]["sd"]**2 + az_results["south"]["sd"]**2) / 2.0
    az_diff = az_results["north"]["gravity"] - az_results["south"]["gravity"]
    
    nt = Time.now()
    nt.format = "iso"
    nt.out_subfmt = "date"
        
    x = PrettyTable()
    x.field_names = ["Azimuth", "Start DateTime", "Sets", "Drops", 
                         "g_eff", "sd", "h_setup"]
    for az in ["north", "south"]:
        x.add_row([az, az_results[az]["iso"], str(az_results[az]["sets"]), 
                    az_results[az]["drops"], 
                    "{:.2f}".format(az_results[az]["gravity"]),
                    "{:.2f}".format(az_results[az]["sd"]),
                    "{:.2f}".format(az_results[az]["h_setup"])])
        
    x.add_row(["result", "", "", "", 
                "{:.2f}".format(az_results["mean"]["gravity"]), 
                "{:.2f}".format(az_results["sd"]),
                "{:.2f}".format(az_results["mean"]["h_setup"])])
        
    with open(path.join(path.split(project)[0], "report.txt"), "w") as f:
        f.write("Recalculation Report\n\n")
            
        f.write(('Site Name:  {0}\nSite Code:  {1}\nCalculation Date:  {2}		\nGravity_eff:  {3:.2f} \xb5Gal		\nStandard Deviation:  {4:.2f} \xb5Gal		\nVertical Gradient:  {5:.2f} \xb5Gal/cm		\nEffective Height:  {6:.2f} cm		\nSetup Height:  {7:.2f} cm		\nHeight_mod:  {8:.2f} cm		\nFactory Height:  {9:.2f} cm\n\n').format(az_results["north"]["name"], 
                    az_results["north"]["code"], nt.value, az_results["mean"]["gravity"],
                    az_results["sd"], wzz, az_results["mean"]["h_eff"], 
                    az_results["mean"]["h_setup"], h_mod, h_fact))
   
        f.write(x.get_string() + "\n\n")
    
        f.write("Azimuth Difference (N-S):  %.2f \xb5Gal" % az_diff)

if __name__ == "__main__":
    main()