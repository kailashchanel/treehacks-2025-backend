from django.templatetags.static import static

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

class ConfigureExotic(APIView):
    def get(self, request):
        print("hi")

        sorted_files = sorted(os.listdir(static("CoRoT-2b_20240807_medium")))
        verified_filepath = static("CoRoT-2b_20240807_medium")

        # CoRoT-2240807035200.FITS

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
        inits_file_path = ""
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
    