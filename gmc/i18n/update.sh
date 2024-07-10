#!/bin/bash
out_name=$(realpath $(dirname $0))/gmc_ru.ts
cd $(dirname $0)/../.. &&
pylupdate5 \
  -verbose \
  -noobsolete \
  gmc/file_widgets/multiple_sources_one_destination.py \
  gmc/file_widgets/one_source_one_destination.py \
  gmc/help_label.py \
  gmc/i18n/schemas_tr.py \
  gmc/main_window.py \
  gmc/markup_objects/point.py \
  gmc/markup_objects/polygon.py \
  gmc/markup_objects/rect.py \
  gmc/markup_objects/tags.py \
  gmc/mdi_area.py \
  gmc/schemas/number_plates/__init__.py \
  gmc/schemas/number_plates/plate_frame.py \
  gmc/schemas/tagged_objects/__init__.py \
  gmc/schemas/tagged_objects/markup_interpolation.py \
  gmc/settings/dialog.py \
  gmc/views/filesystem_view.py \
  gmc/views/filesystem_widget.py \
  gmc/views/image_view.py \
  gmc/views/image_widget.py \
  gmc/views/properties_view.py \
  -ts "$out_name" &&
echo "saved output to $out_name"
