from django.templatetags.static import static

from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

import bokeh.io
from bokeh.io import output_notebook

# from exotic.api.colab import *
from exotic.api.plotting import plot_image
from exotic.exotic import NASAExoplanetArchive, get_wcs

import os
import re
import json
import glob
import random

import urllib
from urllib.request import urlopen
from urllib.error import HTTPError

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.visualization import ZScaleInterval, ImageNormalize
from io import BytesIO

API_STATIC = "exotic_backend/api/static/"
PUBLIC_STATIC = "/static/"

class CoordsInput(APIView):
    def get(self, request):
        convert_fits_to_png = True
        main_run = False

        sorted_files = sorted(os.listdir(f"{API_STATIC}TRES-3b_20100911"))
        verified_filepath = f"{API_STATIC}TRES-3b_20100911"
        output_dir = verified_filepath + "_output/"

        def get_folders_names(directory):
            # List all folders in the directory
            folders = [folder for folder in os.listdir(directory) 
            if os.path.isdir(os.path.join(directory, folder)) and not folder.endswith('_output')] 
            return folders

        if convert_fits_to_png:
            names = get_folders_names(API_STATIC)
            # names = ["CoRoT-2b_20240807_medium"]
            for name in names:
                filepath = f"{API_STATIC}{name}"
                sorted_files_g = sorted(os.listdir(f"{API_STATIC}{name}"))
                uploaded_files = [f for f in sorted_files_g if os.path.isfile(os.path.join(filepath, f))]

                fits_list = []
                first_image = ""
                for f in uploaded_files:
                    # Look for .fits images and keep count
                    if f.lower().endswith(('.fits', '.fits.gz', '.fit')):
                        fits_list.append(f)
                        if first_image == "":
                            first_image = os.path.join(filepath, f)

                # # Process FITS files
                # fits_files = [f for f in os.listdir(verified_filepath) if f.endswith('.fits')]

                total_images = len(fits_list)

                output_dir = filepath + "_output/"
                os.makedirs(output_dir, exist_ok=True)

                for i, fits_file in enumerate(fits_list):
                    with fits.open(os.path.join(filepath, fits_file)) as hdul:
                        image_data = hdul[0].data
                        
                        norm = ImageNormalize(image_data, interval=ZScaleInterval(), 
                                            vmin=np.nanpercentile(image_data, 5),
                                            vmax=np.nanpercentile(image_data, 99))
                        
                        fig, ax = plt.subplots()
                        ax.imshow(image_data, cmap='viridis', norm=norm)
                        ax.axis('off')
                        # ax.set_title(f"Image {i + 1}/{total_images}")
                        
                        # Save the figure as PNG
                        output_path = os.path.join(output_dir, f"image_{i+1}.png")
                        fig.savefig(output_path, dpi=100, bbox_inches='tight', pad_inches=0, 
                                    format='png', transparent=True)
                        plt.close(fig)
                        
                        print(f"Saved: {output_path}")

        if main_run:
            # Directory full of files found, look for .fits and inits.json
            uploaded_files = [f for f in sorted_files if os.path.isfile(os.path.join(verified_filepath, f))]
            fits_count, inits_count, first_image = 0, 0, ""

            # Identify .FITS and inits.json files in user-submitted folder
            inits = []    # array of paths to any inits files found in the directory
            fits_list = []
            for f in uploaded_files:
                # Look for .fits images and keep count
                if f.lower().endswith(('.fits', '.fits.gz', '.fit')):
                    fits_list.append(f)
                if first_image == "":
                    first_image = os.path.join(verified_filepath, f)
                fits_count += 1
                # Look for inits.json file(s)
                if re.search(r"\.json$", f, re.IGNORECASE):
                    inits.append(os.path.join(verified_filepath, f))

            inits_count = len(inits)
            print("fits count" + str(fits_count))
            # display(HTML(f'<p class="output"><br />Found {fits_count} image files and {inits_count} initialization files in the directory.</p>'))

            # Determine if folder has enough .FITS folders to move forward
            if fits_count >= 1:
                fits_files_found = True # exit outer loop and continue

                # Make the output directory if it does not exist already.
                if not os.path.isdir(output_dir):
                    os.mkdir(output_dir)
                # display(HTML(f'<p class="output">Creating output_dir at {output_dir}</p>'))
                output_dir_for_shell = output_dir.replace(" ", "\ ")
            else:
                # display(HTML(f'<p class="error">Failed to find a significant number of .FITS files at {verified_filepath}</p>'))
                input_filepath = input('Enter path to .FITS images(e.g. "EXOTIC/HatP32Dec202017") and press return:  ')

            # Read configuration from inits.json, if available
            inits_file_path = ""
            if inits_count == 1:                 # one inits file exists
            # Deal with inits.json file
                inits_file_path = os.path.join(inits[0])
                inits_file_exists = True
                print("Previous inits.json file exists and will be used.")
            #display(HTML(f'<p class="output">Got an inits.json file here: {inits_file_path}</p>'))
                with open(inits_file_path) as i_file:
                    # display(HTML(f'<p class="output">Loading coordinates and input/output directories from inits file</p>'))
                    inits_data = i_file.read()
                    d = json.loads(inits_data)
                    targ_coords = d["user_info"]["Target Star X & Y Pixel"]
                    comp_coords = d["user_info"]["Comparison Star(s) X & Y Pixel"]
                    input_dir = d["user_info"]["Directory with FITS files"]
                    if input_dir != verified_filepath:
                        # display(HTML(f'<p class="error">The directory with fits files should be {verified_filepath} but your inits file says {input_dir}.</p>'))
                        # display(HTML('<p class="output">This may or may not cause problems.  Just letting you know.<p>'))
                        # display(HTML(f'<p class="output">Coordinates from your inits file:\ntarget: {targ_coords}\ncomps: {comp_coords}<p>'))
                        output_dir = d["user_info"]["Directory to Save Plots"]
            else:
                # display(HTML(f'<p class="output">No valid inits.json file was found, we\'ll create it in the next step.<p>'))
                inits_file_exists = False

        # def post(self, request):

            Telescope = 'MicroObservatory' #@param ["Select a Telescope", "MicroObservatory", "Exoplanet Watch .4 Meter"]
            Star = verified_filepath.split("/")[3].split('b')[0] #@param {type:"string"}
            Target = Star.strip()

            j = 0
            while not os.path.exists(first_image):
                first_image = verified_filepath + '/' + fits_list[j]
                j += 1

            OBJECT_Name = verified_filepath.split("/")[3].split('b')[0] + 'b'
            print(OBJECT_Name)

            def get_star_chart_urls(telescope, star_target):
                if telescope == 'MicroObservatory':
                    t_fov=56.44
                    t_maglimit=15
                    t_resolution=150
                elif telescope == 'Exoplanet Watch .4 Meter':
                    t_fov=38.42
                    t_maglimit=15
                    t_resolution=150
                else:
                    # Should not get here
                    t_fov=56.44
                    t_maglimit=15
                    t_resolution=150
                json_url = f"https://app.aavso.org/vsp/api/chart/?star={star_target}&scale=D&orientation=CCD&type=chart&fov={t_fov}&maglimit={t_maglimit}&resolution={t_resolution}&north=down&east=left&lines=True&format=json"
                starchart_url = f"https://app.aavso.org/vsp/?star={star_target}&scale=D&orientation=CCD&type=chart&fov={t_fov}&maglimit={t_maglimit}&resolution={t_resolution}&north=down&east=left&lines=True"
                return [json_url, starchart_url]

            def get_star_chart_image_url(json_url):
                with urllib.request.urlopen(json_url) as url:
                    starchart_data = json.load(url)
                    image_uri = starchart_data["image_uri"].split('?')[0]
                    return(image_uri)

            if not inits_file_exists:
                planetary_params = ""
                while not planetary_params:
                    target_is_valid = False

                    while not target_is_valid:
                        target=OBJECT_Name
                #################################Jeff Edit Ends
                        if target != "":
                            target_is_valid = True
                        else:
                            starchart_image_url_is_valid = False

                    targ = NASAExoplanetArchive(planet=target)

                    target = targ.planet_info()[0]

                    if targ.resolve_name():
                        p_param_string = targ.planet_info(fancy=True)
                        planetary_params = '"planetary_parameters": ' + p_param_string
                        p_param_dict = json.loads(p_param_string)
                        print(p_param_dict)
                        planetary_params = {"planetary_parameters": p_param_dict}

                if Telescope != 'Select a Telescope' and Target:
                    starchart_image_url = ''
                    starchart_image_url_is_valid = False
                    prompt_for_url = True

                    starchart_urls = get_star_chart_urls(Telescope,Target)
                    try:
                        # Generate the starchart image url
                        starchart_image_url = get_star_chart_image_url(starchart_urls[0])
                        starchart_image_url_is_valid = True
                        prompt_for_url = False
                        print("StarChart Image Url: " + str(starchart_image_url))
                    except HTTPError:
                        prompt_for_url = True

                    while prompt_for_url:
                        starchart_image_url = input('Enter a valid starchart image URL and press return: ')
                        if starchart_image_url.startswith('https://') and starchart_image_url.endswith('png'):
                            starchart_image_url_is_valid = True
                            prompt_for_url = False
                        else:
                            starchart_image_url_is_valid = False

                    if fits_files_found and starchart_image_url_is_valid:

                        # set up bokeh
                        # bokeh.io.output_notebook()
                        sample_data = False

                        # show images
                        if first_image:
                            obs = ""

                            # this coords should come from POST payload from app
                            targ_coords = "[245, 190]"
                            comp_coords = "[[228, 198], [203, 174]]"

                                
                                # with open("/path/to/file.json", "w+") as f:
                                #    json.dump({planetary_params, }, f)
                            
                            # inits_file_path = make_inits_file(planetary_params, verified_filepath, output_dir, first_image, targ_coords, comp_coords, obs, sample_data, aavso_obs_code="", sec_obs_code="")

                            def extract_observation_date(filepath):
                                # Extracts the last part of the path assuming it follows the format ".../TRES-3b_YYYYMMDD"
                                return filepath.rstrip('/').split('_')[-1][:4] + '-' + filepath.rstrip('/').split('_')[-1][4:6] + '-' + filepath.rstrip('/').split('_')[-1][6:]


                            def save_inits_json(planetary_parameters, verified_filepath, output_dir, targ_coords, comp_coords):
                                os.makedirs(output_dir, exist_ok=True)
                                
                                observation_date = extract_observation_date(verified_filepath)
                                print(observation_date)
                                
                                data = {
                                    "planetary_parameters": planetary_parameters["planetary_parameters"],
                                    "user_info": {
                                        "Directory with FITS files": verified_filepath,
                                        "Directory to Save Plots": output_dir,
                                        "Directory of Flats": None,
                                        "Directory of Darks": os.path.join(verified_filepath, "darks"),
                                        "Directory of Biases": None,
                                        "AAVSO Observer Code (N/A if none)": "N/A",
                                        "Secondary Observer Codes (N/A if none)": "N/A",
                                        "Observation date": observation_date,
                                        "Camera Type (CCD or DSLR)": "CCD",
                                        "Pixel Binning": "1x1",
                                        "Filter Name (aavso.org/filters)": "V",
                                        "Observing Notes": "These observations were conducted with MicroObservatory, a robotic telescope network managed by the Harvard-Smithsonian Center for Astrophysics on behalf of NASA's Universe of Learning. This work is supported by NASA under award number NNX16AC65A to the Space Telescope Science Institute.",
                                        "Plate Solution? (y/n)": "y",
                                        "Add Comparison Stars from AAVSO? (y/n)": "y",
                                        "Target Star X & Y Pixel": json.loads(targ_coords),
                                        "Comparison Star(s) X & Y Pixel": json.loads(comp_coords),
                                        "Demosaic Format": None,
                                        "Demosaic Output": None
                                    },
                                    "optional_info": {
                                        "Pixel Scale (Ex: 5.21 arcsecs/pixel)": None,
                                        "Filter Minimum Wavelength (nm)": None,
                                        "Filter Maximum Wavelength (nm)": None
                                    },
                                }
                                
                                output_path = os.path.join(verified_filepath, "inits.json")
                                with open(output_path, "w") as json_file:
                                    json.dump(data, json_file, indent=4)
                                
                                print(f"inits.json saved to: {output_path}")

                                return output_path

                            inits_file_path = save_inits_json(planetary_params, verified_filepath, output_dir, targ_coords, comp_coords)

            print("-------------- END OF SECTION --------------")

            if not inits_file_path: # this skips this section, delete not to include exotic analysis step

                sample_data = False

                print("Path to the inits file(s) that will be used: " + inits_file_path)

                commands = []
                with open(inits_file_path) as i_file:
                    inits_data = i_file.read()
                    d = json.loads(inits_data)
                    date_obs = d["user_info"]["Observation date"]
                    planet = d["planetary_parameters"]["Planet Name"]
                    output_dir = d["user_info"]["Directory to Save Plots"]
                    if not os.path.isdir(output_dir):
                        os.makedirs(output_dir)
                    inits_file_for_shell = inits_file_path.replace(" ", "\\ ")
                    run_exotic = str(f"exotic -red {inits_file_for_shell} -ov")
                    debug_exotic_run = str(f"!exotic -red \"{inits_file_path}\" -ov")

                    commands.append({"inits_file_for_shell": inits_file_for_shell, "output_dir": output_dir,
                                    "planet": planet, "date_obs": date_obs,
                                    "run_exotic": run_exotic, "debug_exotic_run": debug_exotic_run
                                    })
                    print(f"{debug_exotic_run}")
                    #!eval "$run_exotic"
                    os.system(run_exotic)

                    file_for_submission = os.path.join(output_dir,"AAVSO_"+planet+"_"+date_obs+".txt")
                    lightcurve = os.path.join(output_dir,"FinalLightCurve_"+planet+"_"+date_obs+".png")
                    fov = os.path.join(output_dir,"temp/FOV_"+planet+"_"+date_obs+"_LinearStretch.png")
                    triangle = os.path.join(output_dir,"temp/Triangle_"+planet+"_"+date_obs+".png")

                    print(f"aavso output: {file_for_submission}\nlightcurve: {lightcurve}\nfov: {fov}\ntriangle: {triangle}")

                    if not (os.path.isfile(lightcurve) and os.path.isfile(fov) and os.path.isfile(triangle)):
                        print(f"Something went wrong with {planet} {date_obs}.\nCopy the command below into a new cell and run to find the error:\n{debug_exotic_run}\n")

                    # imageA = widgets.Image(value=open(lightcurve, 'rb').read())
                    # imageB = widgets.Image(value=open(fov, 'rb').read())
                    # hbox = HBox([imageB, imageA])
                    # display(hbox)
                    # display(Image(filename=triangle))

                # Allow download of lightcurve data
                # def on_dl_button_clicked(b):
                #     # Display the message within the output widget.
                #     if os.path.isfile(file_for_submission):
                #         files.download(file_for_submission)

                # dl_button = widgets.Button(description="Download data")
                # dl_button.on_click(on_dl_button_clicked)

        return Response(status=status.HTTP_200_OK)
    

class Images(APIView):
    def get(self, request):
        Telescope = 'MicroObservatory' #@param ["Select a Telescope", "MicroObservatory", "Exoplanet Watch .4 Meter"]
        Star = ""

        def middle_image(directory):
            # List all subdirectories in the given directory
            subfolders = [folder for folder in os.listdir(directory) if (os.path.isdir(os.path.join(directory, folder)) and folder.endswith('_output'))]
            
            if not subfolders:
                return None  # If there are no subdirectories, return None

            # Choose a random folder
            random_folder = random.choice(subfolders)
            folder_path = os.path.join(directory, random_folder)

            # List all .png files in the chosen folder
            png_files = [file for file in os.listdir(folder_path) if file.endswith('.png')]

            if not png_files:
                return None  # If there are no .png files, return None

            # Sort the files by name (assuming they are named like "image_1.png", "image_2.png", etc.)
            png_files.sort()

            # Find the middle image
            middle_index = len(png_files) // 2
            middle_image = png_files[middle_index]
            
            return middle_image, folder_path
        
        def get_star_chart_urls(telescope, star_target):
            if telescope == 'MicroObservatory':
                t_fov=56.44
                t_maglimit=15
                t_resolution=150
            elif telescope == 'Exoplanet Watch .4 Meter':
                t_fov=38.42
                t_maglimit=15
                t_resolution=150
            else:
                # Should not get here
                t_fov=56.44
                t_maglimit=15
                t_resolution=150
            json_url = f"https://app.aavso.org/vsp/api/chart/?star={star_target}&scale=D&orientation=CCD&type=chart&fov={t_fov}&maglimit={t_maglimit}&resolution={t_resolution}&north=down&east=left&lines=True&format=json"
            starchart_url = f"https://app.aavso.org/vsp/?star={star_target}&scale=D&orientation=CCD&type=chart&fov={t_fov}&maglimit={t_maglimit}&resolution={t_resolution}&north=down&east=left&lines=True"
            return [json_url, starchart_url]

        def get_star_chart_image_url(json_url):
            with urllib.request.urlopen(json_url) as url:
                starchart_data = json.load(url)
                image_uri = starchart_data["image_uri"].split('?')[0]
                return(image_uri)

        img, folder_name = middle_image(API_STATIC)

        Star = folder_name.split("/")[3].split('b')[0] #@param {type:"string"}
        Target = Star.strip()

        starchart_urls = get_star_chart_urls(Telescope, Target)
        # Generate the starchart image url
        starchart_image_url = get_star_chart_image_url(starchart_urls[0])

        return Response(status=status.HTTP_200_OK, data={"img": f"{folder_name.replace(API_STATIC, PUBLIC_STATIC)}/{img}", "starchart": str(starchart_image_url)})
