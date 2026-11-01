; Original public-PDB authoring from two original generated corpus sources.
; Load historical_2_9_6.scm first. src is its genuine v8 F32 zlib Save As;
; asym is its genuine v7 U16 asymmetric source. No header bytes are patched.
; Public precision conversion preserves the loaded image's zlib choice;
; public raw pixel getters/setters preserve every independently authored U16 value.
(define (historical-v8-u16-asymmetric src asym output-root)
(let* ((out (string-append output-root "/historical-2-9-6-v008-u16-asymmetric-zlib.xcf"))
       (image (car (gimp-file-load RUN-NONINTERACTIVE src src)))
       (layer (vector-ref (cadr (gimp-image-get-layers image)) 0))
       (reference (car (gimp-file-load RUN-NONINTERACTIVE asym asym)))
       (reference-owner (vector-ref (cadr (gimp-image-get-layers reference)) 0)))
 (gimp-image-convert-precision image 250)
 (gimp-item-set-name layer "Original asymmetric U16 samples")
 (let loopy ((y 0)) (if (< y 6) (begin
  (let loopx ((x 0)) (if (< x 8) (begin
   (let ((pixel (gimp-drawable-get-pixel reference-owner x y)))
    (gimp-drawable-set-pixel layer x y (car pixel) (cadr pixel)))
   (loopx (+ x 1)))))
  (loopy (+ y 1)))))
 (gimp-image-delete reference)
 (gimp-image-set-metadata image "")
 (gimp-xcf-save RUN-NONINTERACTIVE image layer out out)
 (gimp-image-delete image)
 (historical-highdepth-readback out (string-append output-root "/v8-u16-asymmetric-pass1.all-pixels.scm"))
 (historical-highdepth-readback out (string-append output-root "/v8-u16-asymmetric-pass2.all-pixels.scm"))
 (let* ((loaded (car (gimp-file-load RUN-NONINTERACTIVE out out)))
        (owner (vector-ref (cadr (gimp-image-get-layers loaded)) 0)))
  (gimp-image-set-metadata loaded "")
  (file-png-save RUN-NONINTERACTIVE loaded owner (string-append output-root "/historical-2-9-6-v008-u16-asymmetric-zlib.png") (string-append output-root "/historical-2-9-6-v008-u16-asymmetric-zlib.png") 0 9 0 0 0 0 0)
  (gimp-image-delete loaded))
 (gimp-message "SOL10_V8_U16_ASYMMETRIC_COMPLETE")))
