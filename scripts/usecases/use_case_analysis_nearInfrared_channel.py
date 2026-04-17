import cv2
import os
import numpy as np
import matplotlib.pyplot as plt

# --- Configuration ---
# You can change the input image name here.
INPUT_IMAGE = "usecasecropped.png"
OUTPUT_IMAGE = "nomralised_usecaseRGN_isolated.jpg"
# ---------------------

def process_image(input_path, output_path, use_heatmap=False, auto_download_sam=False, script_dir="."):
    """
    Reads an image, extracts the third channel, and optionally applies a heatmap.
    
    Args:
        input_path (str): Path to the input image.
        output_path (str): Path where the processed image will be saved.
        use_heatmap (bool): Whether to apply a heatmap colormap.
        auto_download_sam (bool): Bypass interactive prompt to download SAM model.
        script_dir (str): Directory where the script resides for local saves.
    """
    # Load the image
    img = cv2.imread(input_path)
    
    if img is None:
        print(f"Error: Could not load image from {input_path}")
        return

    # In OpenCV, images are loaded in BGR order by default.
    # The third channel (index 2) is the Red channel (often NIR or Blue in multispectral setups).
    # Extract the third channel
    third_channel = img[:, :, 2]
    h, w = third_channel.shape
    
    # --- INTERACTIVE ROI SELECTION ---
    print("Please select 10 areas of interest (ROIs) for Group 1 (Left Façade).")
    group1_rois = []
    for i in range(10):
        window_name = f"Group 1 (Left Façade) - Select ROI {i+1} of 10"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 800, int(800 * h / w))
        r = cv2.selectROI(window_name, img, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow(window_name)
        group1_rois.append(r)
        
    print("Please select 10 areas of interest (ROIs) for Group 2 (Right Façade).")
    group2_rois = []
    for i in range(10):
        window_name = f"Group 2 (Right Façade) - Select ROI {i+1} of 10"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 800, int(800 * h / w))
        r = cv2.selectROI(window_name, img, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow(window_name)
        group2_rois.append(r)
        
    print("Please select 10 areas of interest (ROIs) for Group 3 (Glass).")
    group3_rois = []
    for i in range(10):
        window_name = f"Group 3 (Glass) - Select ROI {i+1} of 10"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 800, int(800 * h / w))
        r = cv2.selectROI(window_name, img, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow(window_name)
        group3_rois.append(r)

    print("\nInitializing SAM model...")
    use_sam = False
    try:
        from ultralytics import SAM
        model_path = os.path.join(script_dir, 'sam_b.pt')
        
        # Check if the model is present, prompt if not
        if not os.path.exists(model_path):
            print(f"SAM model not found at {model_path}.")
            if not auto_download_sam:
                ans = input("Do you want to download the SAM model required for semantic segmentation? (y/N): ")
                if ans.lower() != 'y':
                    print("Skipping SAM model download. Falling back to rectangular ROIs.")
                    raise ImportError("User skipped SAM model download.")
        
        # Load the SAM model (downloads automatically if not found and path is just a file name)
        sam_model = SAM('sam_b.pt')
        use_sam = True
        print("SAM model loaded successfully.")
    except ImportError as e:
        if str(e) != "User skipped SAM model download.":
            print("Ultralytics library not found. Falling back to rectangular ROIs.")

    mask_overlay = img.copy()

    def get_avg_values(rois, group_name=""):
        avgs = []
        if "Group 1" in group_name:
            color = np.array([0, 255, 0]) # Green
        elif "Group 2" in group_name:
            color = np.array([255, 0, 0]) # Blue
        else:
            color = np.array([0, 255, 255]) # Yellow
            
        for j, (x, y, w_roi, h_roi) in enumerate(rois):
            if w_roi > 0 and h_roi > 0:
                if use_sam:
                    bboxes = [x, y, x + w_roi, y + h_roi]
                    print(f"Segmenting {group_name} ROI {j+1}...", end='\r')
                    results = sam_model(img, bboxes=bboxes, verbose=False)
                    
                    if len(results) > 0 and results[0].masks is not None:
                        mask = results[0].masks.data[0].cpu().numpy()
                        if mask.shape != third_channel.shape:
                            mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
                        mask_bool = mask > 0.5
                        
                        mask_overlay[mask_bool] = mask_overlay[mask_bool] * 0.5 + color * 0.5
                        cv2.rectangle(mask_overlay, (x, y), (x+w_roi, y+h_roi), color.tolist(), 2)

                        roi_pixels = third_channel[mask_bool]
                        if len(roi_pixels) > 0:
                            avgs.append(np.mean(roi_pixels))
                        else:
                            avgs.append(0)
                    else:
                        cv2.rectangle(mask_overlay, (x, y), (x+w_roi, y+h_roi), color.tolist(), 2)
                        roi_pixels = third_channel[y:y+h_roi, x:x+w_roi]
                        avgs.append(np.mean(roi_pixels))
                else:
                    cv2.rectangle(mask_overlay, (x, y), (x+w_roi, y+h_roi), color.tolist(), 2)
                    roi_pixels = third_channel[y:y+h_roi, x:x+w_roi]
                    avgs.append(np.mean(roi_pixels))
            else:
                avgs.append(0)
                
        if use_sam:
            print(f"Segmenting {group_name} complete.                ")
        return avgs

    group1_avgs = get_avg_values(group1_rois, "Group 1")
    group2_avgs = get_avg_values(group2_rois, "Group 2")
    group3_avgs = get_avg_values(group3_rois, "Group 3")
    
    for i, val in enumerate(group1_avgs):
        print(f"Group 1 (Left) ROI {i+1} Avg: {val:.2f}")
    for i, val in enumerate(group2_avgs):
        print(f"Group 2 (Right) ROI {i+1} Avg: {val:.2f}")
    for i, val in enumerate(group3_avgs):
        print(f"Group 3 (Glass) ROI {i+1} Avg: {val:.2f}")

    # Perform One-Way ANOVA and Tukey's HSD Test
    plot_title = 'Distribution of Near-Infrared ROI Values across Regions'
    try:
        from scipy.stats import f_oneway, tukey_hsd
        
        # 1. One-Way ANOVA
        anova_stat, anova_p = f_oneway(group1_avgs, group2_avgs, group3_avgs)
        print("\n--- One-Way ANOVA Results ---")
        print(f"F-statistic: {anova_stat:.4f}, p-value: {anova_p:.4f}")
        
        # 2. Tukey's HSD Test
        res = tukey_hsd(group1_avgs, group2_avgs, group3_avgs)
        print("\n--- Tukey's HSD Test Results ---")
        print(res)
        
        # For multiple pairwise comparisons, we log it to console and just put ANOVA p-value in title
        plot_title = f'Distribution of Near-Infrared ROI Values across Regions\n(ANOVA p={anova_p:.4f})'
    except ImportError:
        print("\nSciPy not installed. Skipping statistical tests.")
    except Exception as e:
        print(f"\nCould not perform statistical tests: {e}")

    # Generate Box Plot with Jitter
    plt.figure(figsize=(6, 6))
    data = [group1_avgs, group2_avgs, group3_avgs]
    labels = ['Left Façade', 'Right Façade', 'Glass']
    
    plt.boxplot(data, tick_labels=labels, showfliers=False) if hasattr(plt.Axes, 'boxplot') else plt.boxplot(data, labels=labels, showfliers=False)
    
    # Add jitter
    for i, group_data in enumerate(data):
        x = np.random.normal(i + 1, 0.04, size=len(group_data))
        plt.scatter(x, group_data, alpha=0.7, zorder=2)

    plt.ylabel('Average Near-Infrared Value')
    plt.title(plot_title)
    plt.ylim(0, 60)
    
    box_output_path = os.path.join(script_dir, "roi_boxplot.png")
    plt.savefig(box_output_path)
    print(f"Saved box plot to {box_output_path}")
    # ---------------------------------

    # 1. Pixelation: Downsample the channel
    # Define pixelation factor (lower means more pixelated)
    scale_factor = 0.25  # Downsample to 10% of original size
    w_small = max(1, int(w * scale_factor))
    h_small = max(1, int(h * scale_factor))
    pixelated = cv2.resize(third_channel, (w_small, h_small), interpolation=cv2.INTER_NEAREST)
    
    # 2. Normalization: Min-max normalization on the pixelated data
    normalized = cv2.normalize(pixelated, None, 0, 255, cv2.NORM_MINMAX)
    
    # 3. Smoothing: Upsample back to original size with interpolation
    smoothed = cv2.resize(normalized, (w, h), interpolation=cv2.INTER_CUBIC)
    
    if use_heatmap:
        # Apply a colormap (VIRIDIS as set in previous steps)
        colormap = cv2.COLORMAP_VIRIDIS
        processed_img = cv2.applyColorMap(smoothed, colormap)
        
        # 4. Add Color Scale (Legend)
        # Create a color bar
        bar_width = 75
        # Create a vertical gradient from 255 down to 0
        gradient = np.linspace(255, 0, h).astype(np.uint8).reshape(-1, 1)
        # Repeat to match bar width
        gradient_bar = np.repeat(gradient, bar_width, axis=1)
        # Apply the same colormap to the gradient
        color_bar = cv2.applyColorMap(gradient_bar, colormap)
        
        # Add labels to the color bar (Max/Min)
        cv2.putText(color_bar, "Max NIR", (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(color_bar, "Min NIR", (5, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        
        # Create a black separator line
        separator = np.ones((h, 5, 3), dtype=np.uint8) * 255
        
        # Concatenate heatmap, separator, and color bar
        processed_img = np.hstack((processed_img, separator, color_bar))
        
        print("Applied smoothed heatmap with color scale to the processed third channel.")
    else:
        processed_img = smoothed
        print("Generated smoothed grayscale from the third channel.")

    # Save the result
    cv2.imwrite(output_path, processed_img)
    print(f"Saved processed image to {output_path}")

    # Display the final image
    # Resize for display if needed
    h_final, w_final = processed_img.shape[:2]
    display_h = 800
    display_w = int(w_final * (display_h / h_final))
    display_resized = cv2.resize(processed_img, (display_w, display_h))
    
    mask_overlay_path = os.path.join(script_dir, "sam_masks_overlay.jpg")
    cv2.imwrite(mask_overlay_path, mask_overlay)
    print(f"Saved SAM masks overlay to {mask_overlay_path}")
    
    overlay_h, overlay_w = mask_overlay.shape[:2]
    overlay_display_h = 800
    overlay_display_w = int(overlay_w * (overlay_display_h / overlay_h))
    overlay_resized = cv2.resize(mask_overlay, (overlay_display_w, overlay_display_h))

    cv2.imshow("SAM Masks Overlay", overlay_resized)
    cv2.imshow("Processed Heatmap", display_resized)
    print("Displaying heatmap and SAM masks. Press any key in the image windows to close them and view the box plot...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print("Displaying the box plot. Close the plot window to exit.")
    plt.show()
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, INPUT_IMAGE)
    output_path = os.path.join(script_dir, OUTPUT_IMAGE)
    
    # Check if input file exists
    if not os.path.exists(input_path):
        print(f"Warning: Input file '{input_path}' not found. Please ensure it exists.")
    else:
        # Defaulting use_heatmap=True and auto_download_sam=False (set to True in args previously if flag passed, we default to False)
        # Assuming user's previous intention for default execution.
        process_image(input_path, output_path, use_heatmap=True, auto_download_sam=False, script_dir=script_dir)
