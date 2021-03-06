# @file Polyfit.py
# @brief methods to find polynomials from lanes and reliably fit the polynomials.
# @author Aparajith Sridharan
#         s.aparajith@live.com
# @date 30.12.2020
from Transforms import TransformationPipeline
import cv2
import numpy as np
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
#debug enables printing, image viewing for debugging
debug = 0
########################
# Class definitions
########################
# Define a class to receive the characteristics of each line detection
class Line():
    def __init__(self):
        # was the line detected in the last iteration?
        self.detected = False
        # average x values of the fitted line over the last n iterations
        self.bestx = None
        # polynomial coefficients averaged over the last n iterations
        self.best_fit = None
        # polynomial coefficients for the most recent fit
        self.current_fit = np.array([0,0,0],dtype=np.float)
        # polynomial coefficients stored for N cycles
        self.running_fit = []
        # radius of curvature of the line in [m]
        self.radius_of_curvature = None
        # difference in fit coefficients between last and new fits
        self.diffs = np.array([0,0,0], dtype='float')
        # Max cycles for smoothing filter
        self.Max_N = 30

    #@brief computes the smoothing value (moving average)
    def smooth(self):
        if len(self.running_fit) > 0:
            self.best_fit = np.mean(self.running_fit, axis=0)

    # @brief adds the new value to filter and computes the smoothing value (moving average)
    def add(self, new_fit):
        self.current_fit = new_fit
        if len(self.running_fit) == self.Max_N:
            # remove first element
            self.running_fit.pop(0)
        # append new element
        self.running_fit.append(new_fit)
        self.smooth()

    #@brief clears the filter storage
    def resetFilter(self):
        self.running_fit = []

    #@brief using y calculates the x values based on the bestfit polynomial.
    def calcPoly(self,ploty):
        self.bestx = self.best_fit[0] * ploty ** 2 + self.best_fit[1] * ploty + self.best_fit[2]

########################
# Function definitions
########################

# Polynomial fit values from the previous frame
# Make sure to grab the actual values from the previous step in your project!
def find_lane_pixels(binary_warped):
    # Take a histogram of the bottom half of the image
    histogram = np.sum(binary_warped[binary_warped.shape[0] // 2:, :], axis=0)
    # Create an output image to draw on and visualize the result
    out_img = np.dstack((binary_warped, binary_warped, binary_warped))
    # Find the peak of the left and right halves of the histogram
    # These will be the starting point for the left and right lines
    midpoint = np.int(histogram.shape[0] // 2)
    leftx_base = np.argmax(histogram[:midpoint])
    rightx_base = np.argmax(histogram[midpoint:]) + midpoint

    # HYPERPARAMETERS
    # Choose the number of sliding windows
    nwindows = 15
    # Set the width of the windows +/- margin
    margin = 100
    # Set minimum number of pixels found to recenter window
    minpix = 50

    # Set height of windows - based on nwindows above and image shape
    window_height = np.int(binary_warped.shape[0] // nwindows)
    # Identify the x and y positions of all nonzero pixels in the image
    nonzero = binary_warped.nonzero()
    nonzeroy = np.array(nonzero[0])
    nonzerox = np.array(nonzero[1])
    # Current positions to be updated later for each window in nwindows
    leftx_current = leftx_base
    rightx_current = rightx_base

    # Create empty lists to receive left and right lane pixel indices
    left_lane_inds = []
    right_lane_inds = []

    # Step through the windows one by one
    for window in range(nwindows):
        # Identify window boundaries in x and y (and right and left)
        win_y_low = binary_warped.shape[0] - (window + 1) * window_height
        win_y_high = binary_warped.shape[0] - window * window_height
        ### TO-DO: Find the four below boundaries of the window ###
        win_xleft_low = leftx_current - margin
        win_xleft_high = leftx_current + margin
        win_xright_low = rightx_current - margin
        win_xright_high = rightx_current + margin
        # Draw the windows on the visualization image
        cv2.rectangle(out_img, (win_xleft_low, win_y_low),(win_xleft_high, win_y_high), (0, 255, 0), 2)
        cv2.rectangle(out_img, (win_xright_low, win_y_low),(win_xright_high, win_y_high), (0, 255, 0), 2)

        # Identify the nonzero pixels in x and y within the window #
        good_left_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) &
                          (nonzerox >= win_xleft_low) & (nonzerox < win_xleft_high)).nonzero()[0]
        good_right_inds = ((nonzeroy >= win_y_low) & (nonzeroy < win_y_high) &
                           (nonzerox >= win_xright_low) & (nonzerox < win_xright_high)).nonzero()[0]

        # Append these indices to the lists
        left_lane_inds.append(good_left_inds)
        right_lane_inds.append(good_right_inds)

        # If you found > minpix pixels, recenter next window on their mean position
        if len(good_left_inds) > minpix:
            leftx_current = np.int(np.mean(nonzerox[good_left_inds]))
        if len(good_right_inds) > minpix:
            rightx_current = np.int(np.mean(nonzerox[good_right_inds]))

    # Concatenate the arrays of indices (previously was a list of lists of pixels)
    try:
        left_lane_inds = np.concatenate(left_lane_inds)
        right_lane_inds = np.concatenate(right_lane_inds)
    except ValueError:
        # Avoids an error if the above is not implemented fully
        pass

    # Extract left and right line pixel positions
    leftx = nonzerox[left_lane_inds]
    lefty = nonzeroy[left_lane_inds]
    rightx = nonzerox[right_lane_inds]
    righty = nonzeroy[right_lane_inds]

    return leftx, lefty, rightx, righty, out_img

#@brief function that fits polynomial using sliding window method
def fit_polynomial(binary_warped):
    # Find our lane pixels first
    leftx, lefty, rightx, righty, out_img = find_lane_pixels(binary_warped)
    fitmiss = False
    left_fit =np.array([1,1,1])
    right_fit = np.array([1, 1, 1])

    if(len(leftx)==0 or len(rightx)==0):
        fitmiss=True
    else:
        # Fit a second order polynomial to each using `np.polyfit` ###
        left_fit = np.polyfit(lefty, leftx, 2)
        right_fit = np.polyfit(righty, rightx, 2)

    # Generate x and y values for plotting
    ploty = np.linspace(0, binary_warped.shape[0] - 1, binary_warped.shape[0])
    try:
        left_fitx = left_fit[0] * ploty ** 2 + left_fit[1] * ploty + left_fit[2]
        right_fitx = right_fit[0] * ploty ** 2 + right_fit[1] * ploty + right_fit[2]
        fitmiss = False
    except TypeError:
        # Avoids an error if `left` and `right_fit` are still none or incorrect
        print('The function failed to fit a line!')
        left_fitx = 1 * ploty ** 2 + 1 * ploty
        right_fitx = 1 * ploty ** 2 + 1 * ploty
        fitmiss = True

    if debug == 1:
        ## Visualization ##
        # Colors in the left and right lane regions
        out_img[lefty, leftx] = [255, 0, 0]
        out_img[righty, rightx] = [0, 0, 255]

        fig,ax = plt.subplots()
        ax.imshow(out_img)
        # Plots the left and right polynomials on the lane lines
        ax.plot(left_fitx, ploty, color='yellow')
        ax.plot(right_fitx, ploty, color='yellow')
        plt.show()
    return ploty,left_fit,right_fit,fitmiss


#@brief polynomial fit for fast searching algorithm
#
def fit_poly(img_shape, leftx, lefty, rightx, righty):
    ### TO-DO: Fit a second order polynomial to each with np.polyfit() ###
    left_fit = np.polyfit(lefty, leftx, 2)
    right_fit = np.polyfit(righty, rightx, 2)
    # Generate x and y values for plotting
    ploty = np.linspace(0, img_shape[0] - 1, img_shape[0])
    return left_fit, right_fit, ploty

#@brief fast search around for polyline drawing ( iteration-2 onwards.)
#
def search_around_poly(binary_warped,left_fit=np.array([0,0,0]),right_fit=np.array([0,0,0])):
    # HYPERPARAMETER
    # Choose the width of the margin around the previous polynomial to search
    margin = 100
    # Grab activated pixels
    nonzero = binary_warped.nonzero()
    nonzeroy = np.array(nonzero[0])
    nonzerox = np.array(nonzero[1])

    ### Set the area of search based on activated x-values ###
    ### within the +/- margin of our polynomial function ###
    left_lane_inds = ((nonzerox > (left_fit[0] * (nonzeroy ** 2) + left_fit[1] * nonzeroy +
                                   left_fit[2] - margin)) & (nonzerox < (left_fit[0] * (nonzeroy ** 2) +
                                                                         left_fit[1] * nonzeroy + left_fit[
                                                                             2] + margin)))
    right_lane_inds = ((nonzerox > (right_fit[0] * (nonzeroy ** 2) + right_fit[1] * nonzeroy +
                                    right_fit[2] - margin)) & (nonzerox < (right_fit[0] * (nonzeroy ** 2) +
                                                                           right_fit[1] * nonzeroy + right_fit[
                                                                               2] + margin)))

    # Again, extract left and right line pixel positions
    leftx = nonzerox[left_lane_inds]
    lefty = nonzeroy[left_lane_inds]
    rightx = nonzerox[right_lane_inds]
    righty = nonzeroy[right_lane_inds]
    fitmiss=True
    ploty = np.linspace(0, binary_warped.shape[0] - 1, binary_warped.shape[0])
    if(len(leftx)==0 or len(rightx)==0):
        fitmiss=True
    else:
        if(np.absolute(np.average(rightx)-np.average(leftx)) < 100):
            fitmiss=True
        else:
            # Fit new polynomials
            left_fit, right_fit, ploty = fit_poly(binary_warped.shape, leftx, lefty, rightx, righty)
            fitmiss=False
    if debug == 1:
        ## Visualization ##
        # Create an image to draw on and an image to show the selection window
        out_img = np.dstack((binary_warped, binary_warped, binary_warped)) * 255
        window_img = np.zeros_like(out_img)
        # Color in left and right line pixels
        out_img[nonzeroy[left_lane_inds], nonzerox[left_lane_inds]] = [255, 0, 0]
        out_img[nonzeroy[right_lane_inds], nonzerox[right_lane_inds]] = [0, 0, 255]

        # Generate a polygon to illustrate the search window area
        # And recast the x and y points into usable format for cv2.fillPoly()
        left_line_window1 = np.array([np.transpose(np.vstack([left_fitx - margin, ploty]))])
        left_line_window2 = np.array([np.flipud(np.transpose(np.vstack([left_fitx + margin,
                                                                        ploty])))])
        left_line_pts = np.hstack((left_line_window1, left_line_window2))
        right_line_window1 = np.array([np.transpose(np.vstack([right_fitx - margin, ploty]))])
        right_line_window2 = np.array([np.flipud(np.transpose(np.vstack([right_fitx + margin,
                                                                         ploty])))])
        right_line_pts = np.hstack((right_line_window1, right_line_window2))

        # Draw the lane onto the warped blank image
        cv2.fillPoly(window_img, np.int_([left_line_pts]), (0, 255, 0))
        cv2.fillPoly(window_img, np.int_([right_line_pts]), (0, 255, 0))
        result = cv2.addWeighted(out_img, 1, window_img, 0.3, 0)

        # Plot the polynomial lines onto the image
        fig2,ax2 = plt.subplots()
        ax2.imshow(result)
        # Plots the left and right polynomials on the lane lines
        #ax2.plot(left_fitx, ploty, color='yellow')
        #ax2.plot(right_fitx, ploty, color='yellow')
        plt.show()
        ## End visualization steps ##

    return ploty,left_fit,right_fit,fitmiss


def fitPolynomialWithPerformance(warped,g_leftx,g_rightx,g_once):
    '''
    Calculates the curvature of polynomial functions in meters.
    '''
    once = 0
    fitmiss=True
    if g_once == 0:
        # feed in the real data
        ploty, g_leftx, g_rightx, fitmiss = fit_polynomial(warped)
    else:
        ploty, g_leftx, g_rightx, fitmiss = search_around_poly(warped,g_leftx,g_rightx)

    if not fitmiss:
        once = 1

    return g_leftx, g_rightx, fitmiss, ploty, once


def measureCurvatureWorld(g_leftx,g_rightx,ploty):
    # Define conversions in x and y from pixels space to meters
    ym_per_pix = 30 / 720  # meters per pixel in y dimension
    xm_per_pix = 3.7 / 910  # meters per pixel in x dimension
    # scale the parabola using "x = mx / (my ** 2) * a * (y ** 2) + (mx / my) * b * y + c"
    left_fit_cr = np.array([(xm_per_pix/(ym_per_pix**2))*g_leftx[0],(xm_per_pix/ym_per_pix)*g_leftx[1],g_leftx[2]])
    right_fit_cr = np.array([(xm_per_pix/(ym_per_pix**2))*g_rightx[0],(xm_per_pix/ym_per_pix)*g_rightx[1],g_rightx[2]])
    # Define y-value where we want radius of curvature
    # We'll choose the maximum y-value, corresponding to the bottom of the image
    y_eval = np.max(ploty)
    # Implement the calculation of R_curve (radius of curvature) #####
    left_curverad = ((1 + (2 * left_fit_cr[0] * y_eval*ym_per_pix + left_fit_cr[1]) ** 2) ** 1.5) / np.absolute(
        2 * left_fit_cr[0])
    right_curverad = ((1 + (2 * right_fit_cr[0] * y_eval*ym_per_pix + right_fit_cr[1]) ** 2) ** 1.5) / np.absolute(
        2 * right_fit_cr[0])
    return left_curverad, right_curverad,

def finalPipeline(img, left=Line(), right=Line(),once=0):
    # Load our image - this should be a new frame since last time!
    Minv, blended, warped = TransformationPipeline(img)
    lfit, rfit, fitmiss, ploty, once=\
        fitPolynomialWithPerformance(warped,left.best_fit,right.best_fit,once)
    # check if the left and right polynomials has any roots together they aren-t parallel!
    r = np.roots(lfit - rfit)
    # take conjugates to find magnitude because roots can be complex
    # check if those roots lie within the frame then deplete performance,
    if((np.sqrt(r[0]*np.conjugate(r[0]))<img.shape[1])
        and (np.sqrt(r[1]*np.conjugate(r[1]))<img.shape[0])):
        fitmiss=1
    if not fitmiss:
        left.add(lfit)
        right.add(rfit)
        left.detected=True
        right.detected = True
        #get the left x and rightx computed to draw the lane lines and do other calculations later.
        left.calcPoly(ploty)
        right.calcPoly(ploty)
        left.radius_of_curvature,right.radius_of_curvature = measureCurvatureWorld(left.best_fit,right.best_fit,ploty)
    else:
        left.detected = False
        right.detected = False
        once=0
    return Minv, left, right,ploty, once, warped


if __name__ == "__main__":
    image = cv2.imread("../test_images/straight_lines1.jpg")
    finalPipeline(image)

    # View your output
    cv2.waitKey()
    cv2.destroyAllWindows()