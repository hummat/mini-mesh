# Interactive 3D Gallery Design

## Overview

Add interactive 3D model viewers for the three showcase objects (Mokka, Dog, Mustard) below the hero banner, using Google's model-viewer library. The 3D view is the default; a toggle allows switching to the existing 2D split-gallery (color/normal hover).

## Requirements

- 3D mode (default): Three `model-viewer` components with auto-rotate and camera controls
- 2D mode (via toggle): Existing split-gallery with hover-to-expand color/normal behavior
- Small toggle button in bottom-right of gallery area
- Preference persisted in localStorage
- Dark mode support matching existing theme

## Structure

```html
<!-- Wrapper for positioning toggle -->
<div class="gallery-container">
  <!-- 3D Gallery (default visible) -->
  <div class="gallery-3d">
    <model-viewer src="assets/mokka.glb" camera-controls auto-rotate tone-mapping="neutral" shadow-intensity="1"></model-viewer>
    <model-viewer src="assets/dog.glb" camera-controls auto-rotate tone-mapping="neutral" shadow-intensity="1"></model-viewer>
    <model-viewer src="assets/mustard.glb" camera-controls auto-rotate tone-mapping="neutral" shadow-intensity="1"></model-viewer>
  </div>

  <!-- 2D Gallery (hidden by default) -->
  <div class="split-gallery">
    <!-- existing split-cell markup unchanged -->
  </div>

  <!-- Toggle button -->
  <button class="gallery-mode-toggle">2D</button>
</div>
```

Button label shows mode you'll switch TO (not current mode).

## Styling

```scss
// Container for relative positioning of toggle
.gallery-container {
  position: relative;
  margin: 1.5rem 0 2.5rem 0; // extra bottom margin for toggle
}

// 3D gallery layout - matches split-gallery dimensions
.gallery-3d {
  display: flex;
  justify-content: center;
  gap: 1rem;
  flex-wrap: wrap;

  model-viewer {
    width: 200px;
    height: 200px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    --poster-color: transparent;
  }
}

// Toggle button - small, bottom-right
.gallery-mode-toggle {
  position: absolute;
  bottom: -2rem;
  right: 0;
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  background: var(--btn-bg);
  border: 1px solid var(--btn-border);
  border-radius: 4px;
  color: var(--text-color);
  cursor: pointer;
  transition: background-color 0.2s ease;

  &:hover {
    background: var(--btn-hover-bg);
  }
}

// Visibility toggling via data attribute on html element
[data-gallery-mode="2d"] .gallery-3d { display: none; }
[data-gallery-mode="2d"] .split-gallery { display: flex; }
[data-gallery-mode="3d"] .gallery-3d { display: flex; }
[data-gallery-mode="3d"] .split-gallery { display: none; }

// Dark mode shadow adjustment
[data-theme="dark"] .gallery-3d model-viewer {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}
```

## JavaScript

```javascript
// Load model-viewer library (in head-custom.html)
<script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/4.1.0/model-viewer.min.js"></script>

// Toggle logic
document.addEventListener('DOMContentLoaded', function() {
  var savedMode = localStorage.getItem('galleryMode') || '3d';
  document.documentElement.setAttribute('data-gallery-mode', savedMode);

  var toggle = document.querySelector('.gallery-mode-toggle');
  if (toggle) {
    toggle.textContent = savedMode === '3d' ? '2D' : '3D';

    toggle.addEventListener('click', function() {
      var current = document.documentElement.getAttribute('data-gallery-mode');
      var newMode = current === '3d' ? '2d' : '3d';
      document.documentElement.setAttribute('data-gallery-mode', newMode);
      localStorage.setItem('galleryMode', newMode);
      toggle.textContent = newMode === '3d' ? '2D' : '3D';
    });
  }
});
```

## Files to Modify

1. `README.md` - Wrap galleries in container, add gallery-3d markup, add toggle button
2. `assets/css/style.scss` - Add gallery-container, gallery-3d, toggle styles, visibility rules
3. `_includes/head-custom.html` - Load model-viewer script, add toggle logic
4. `assets/` - Add mokka.glb, dog.glb, mustard.glb files

## Implementation Order

1. Add model-viewer script to head-custom.html
2. Add toggle JavaScript to head-custom.html
3. Add CSS styles to style.scss
4. Update README.md with new markup structure
5. Add GLB files to assets/
6. Test locally with Jekyll serve
