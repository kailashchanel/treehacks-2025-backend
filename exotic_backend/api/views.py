from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

import bokeh.io
from bokeh.io import output_notebook

from exotic.api.plotting import plot_image
from exotic.exotic import NASAExoplanetArchive, get_wcs

import os
import re
import json
import glob

import urllib
from urllib.request import urlopen
from urllib.error import HTTPError

class ConfigureExotic(APIView):
    def get(self, request):
        print("hi")

        sorted_files = []
        verified_filepath = ""

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
            input_filepath = input('Enter path to .FITS images in Google Drive (e.g. "EXOTIC/HatP32Dec202017") and press return:  ')

        # Read configuration from inits.json, if available
        if inits_count == 1:                 # one inits file exists
        # Deal with inits.json file
            inits_file_path = os.path.join(verified_filepath, inits[0])
            inits_file_exists = True
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

        return Response(status=status.HTTP_200_OK)

    Telescope = 'MicroObservatory' #@param ["Select a Telescope", "MicroObservatory", "Exoplanet Watch .4 Meter"]
    Star = '' #@param {type:"string"}
    Target = Star.strip()
    j = 0
    while not os.path.exists(first_image):
        first_image = verified_filepath + '/' + fits_list[j]
        j += 1

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
                bokeh.io.output_notebook()
                sample_data = False

                # show images
                if first_image:
                    obs = ""

                    # request coordinates and verify the entries are valid
                    success = False
                    while not success:
                        targ_coords = input("Enter coordinates for target star - in the format [424,286] - and press return:  ")

                        # check syntax and coords
                        targ_coords = targ_coords.strip()
                        tc_syntax = re.search(r"\[\d+, ?\d+\]$", targ_coords)
                        if tc_syntax:
                            success = True

                    # request coordinates and verify the entries are valid
                    success = False
                    while not success:
                        comp_coords = input("Enter coordinates for the comparison stars - in the format [[326,365],[416,343]] - and press return:  ")

                        # check syntax
                        comp_coords = comp_coords.strip()
                        cc_syntax = re.search(r"\[(\[\d+, ?\d+\],? ?)+\]$", comp_coords)
                        if cc_syntax:
                            success = True

                    inits_file_path = make_inits_file(planetary_params, verified_filepath, output_dir, first_image, targ_coords, comp_coords, obs, aavso_obs_code, sec_obs_code, sample_data)
