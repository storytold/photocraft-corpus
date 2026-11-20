; Original public-PDB verification/preview helper for the ordinary GUI v008 save.
; First load historical_2_9_6.scm, which defines historical-highdepth-readback.
; The source must be authored by that generator, then saved in stock GIMP2.9.6
; with the normal Save As better-compression option; this helper never writes XCF.
(define (historical-v8-readback-and-preview xcf facts-file png)
 (historical-highdepth-readback xcf facts-file)
 (let* ((image (car (gimp-file-load RUN-NONINTERACTIVE xcf xcf)))
        (layer (vector-ref (cadr (gimp-image-get-layers image)) 0)))
  (gimp-image-set-metadata image "")
  (file-png-save RUN-NONINTERACTIVE image layer png png 0 9 0 0 0 0 0)
  (gimp-image-delete image)))
