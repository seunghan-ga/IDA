import numpy as np
import cv2
import os
import imutils
import scipy.fftpack

from tensorflow.keras.preprocessing.image import ImageDataGenerator


class Image:

    def registration(self, test_image, ref_image):
        """
        dataset 이미지와 test 이미지의 구도를 맞춤
        Keyword arguments:
        :param test_image: 테스트 이미지
        :param ref_image: 기준 이미지
        :return: 변환된 테스트 이미지
        """
        # Convert to grayscale.
        if len(test_image.shape) == 3:
            img1 = cv2.cvtColor(test_image, cv2.COLOR_BGR2GRAY)
            img2 = cv2.cvtColor(ref_image, cv2.COLOR_BGR2GRAY)
        else:
            img1 = test_image
            img2 = ref_image

        height, width = img2.shape
        orb_detector = cv2.ORB_create(5000)

        # Find keypoints and descriptors.
        # The first arg is the image, second arg is the mask
        #  (which is not reqiured in this case).
        kp1, d1 = orb_detector.detectAndCompute(img1, None)
        kp2, d2 = orb_detector.detectAndCompute(img2, None)

        # Match features between the two images.
        # We create a Brute Force matcher with
        # Hamming distance as measurement mode.
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        # Match the two sets of descriptors.
        matches = matcher.match(d1, d2)

        # Sort matches on the basis of their Hamming distance.
        matches.sort(key=lambda x: x.distance)

        # Take the top 90 % matches forward.
        matches = matches[:int(len(matches) * 50)]
        no_of_matches = len(matches)

        # Define empty matrices of shape no_of_matches * 2.
        p1 = np.zeros((no_of_matches, 2))
        p2 = np.zeros((no_of_matches, 2))

        for i in range(len(matches)):
            p1[i, :] = kp1[matches[i].queryIdx].pt
            p2[i, :] = kp2[matches[i].trainIdx].pt

        # Find the homography matrix.
        homography, mask = cv2.findHomography(p1, p2, cv2.RANSAC)

        # Use this matrix to transform the
        # colored image wrt the dataset image.
        transformed_img = cv2.warpPerspective(test_image, homography, (width, height))

        return transformed_img

    def image_comparison(self, img_A, img_B):
        """
        이미지 A 와 B를 XOR
        Keyword arguments:
        :param  img_A:  테스트 이미지
        :param  img_B:  기준 이미지
        :return diff :  두 이미지의 차이 이미지
        """
        gray_A = cv2.equalizeHist(cv2.cvtColor(img_A, cv2.COLOR_BGR2GRAY))
        gray_A_blur = cv2.GaussianBlur(gray_A, (5, 5), 0)
        binary_A = cv2.adaptiveThreshold(gray_A_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 5, 2)

        # dataset images
        gray_B = cv2.equalizeHist(cv2.cvtColor(img_B, cv2.COLOR_BGR2GRAY))
        gray_B_blur = cv2.GaussianBlur(gray_B, (5, 5), 0)
        binary_B = cv2.adaptiveThreshold(gray_B_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 5, 2)

        # opening = cv2.morphologyEx(diff, cv2.MORPH_OPEN, kernel2)
        test_img = np.expand_dims(binary_A, 2)
        ref_img = np.expand_dims(binary_B, 2)

        # XOR method
        diff = cv2.bitwise_xor(test_img, ref_img)

        return diff

    def image_filter(self, diff):
        """
        XOR 후  주요 특징만 추출
        Keyword arguments:
        :param diff: XOR 이미지
        :return filter7: 필터링 된 이미지
        """
        # kernel
        kernel1 = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        kernel2 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        kernel3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29))
        kernel4 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        kernel5 = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))

        # filtering
        filter1 = cv2.medianBlur(diff, 5)  # image, ksize
        filter2 = cv2.morphologyEx(filter1, cv2.MORPH_CLOSE, kernel1)
        filter3 = cv2.morphologyEx(filter2, cv2.MORPH_OPEN, kernel2)
        filter4 = cv2.medianBlur(filter3, 5)  # image, ksize
        filter5 = cv2.morphologyEx(filter4, cv2.MORPH_CLOSE, kernel3)
        filter6 = cv2.morphologyEx(filter5, cv2.MORPH_OPEN, kernel4)
        filter7 = cv2.morphologyEx(filter6, cv2.MORPH_OPEN, kernel5)

        return filter7

    def image_defect(self, filter7, img_A, size, correction, filename1, filename2, crop_path, origin_path, result_path=""):
        """
        XOR 후 추출된 특징을 자름
        Keyword arguments:
        :param filter7: 필터링 된 XOR 이미지
        :param img_A: 테스트 이미지
        :param size: 결함 부분 이미지 크기
        :param correction: 자르는 부분의 여백
        :param filename1: 결함 이미지 이름
        :param filename2: 결함이 표시된 테스트 이미지
        :return :
        """
        img_temp = img_A.copy()
        cnts = cv2.findContours(filter7, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        d = []

        i = 0
        for c in cnts:
            (x, y, w, h) = cv2.boundingRect(c)

            if (y - correction < 0) or (x - correction < 0):
                continue
            else:
                temp_img = img_temp[(y - correction):(y + h + correction), (x - correction):(x + w + correction), :]
                temp_resized = cv2.resize(temp_img, (size, size))
                d.append(temp_resized)
                crop_file_name = filename1 + '_' + str(i) + '.jpg'
                cv2.imwrite(os.path.join(crop_path, crop_file_name), temp_resized)
                i += 1
                # save
                cv2.rectangle(img_A, (x, y), (x + w, y + h), (0, 0, 255), 2)

        cv2.imwrite(os.path.join(origin_path, filename2), img_A)

        return img_A, d

    def generator(self, temp_resized, count, path, crop_name):
        """
        Keras Image Generator
        Keyword arguments:
        :param temp_resized: 결함 있는 이미지
        :param count: 생성할 이미지 수
        :param path: 저장 위치
        :param crop_name: 생성된 이미지의 이름
        :return:
        """
        sample = np.expand_dims(temp_resized, 0)
        datagen = ImageDataGenerator(rotation_range=180, zoom_range=0.3)
        it = datagen.flow(sample, batch_size=1)
        image_generator = []

        for l in range(count):
            batch = it.next()
            image_gen = batch[0].astype('uint8')
            image_generator.append(image_gen)
            cv2.imwrite(path + '/' + crop_name + '_' + str(l) + '.jpg', image_gen)

        return


class lightness:
    def lightness_color(self, img, gamma_1=0.3, gamma_2=1.5):
        # Convert image to RGB to YUV
        img_YUV = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
        y, u, v = cv2.split(img_YUV)

        # Number of rows and columns
        rows = y.shape[0]
        cols = y.shape[1]

        # Convert image to 0 to 1, then do log(1 + I)
        imgLog = np.log1p(np.array(y, dtype='float') / 255)

        # Create Gaussian mask of sigma = 10
        M = 2 * rows + 1
        N = 2 * cols + 1
        sigma = 10
        (X, Y) = np.meshgrid(np.linspace(0, N - 1, N), np.linspace(0, M - 1, M))
        Xc = np.ceil(N / 2)
        Yc = np.ceil(M / 2)
        gaussianNumerator = (X - Xc) ** 2 + (Y - Yc) ** 2

        # Low pass and high pass filters
        LPF = np.exp(-gaussianNumerator / (2 * sigma * sigma))
        HPF = 1 - LPF

        # Move origin of filters so that it's at the top left corner to match with the input image
        LPF_shift = np.fft.ifftshift(LPF.copy())
        HPF_shift = np.fft.ifftshift(HPF.copy())

        # Filter the image and crop
        img_FFT = np.fft.fft2(imgLog.copy(), (M, N))
        img_LF = np.real(np.fft.ifft2(img_FFT.copy() * LPF_shift, (M, N)))  # low frequency
        img_HF = np.real(np.fft.ifft2(img_FFT.copy() * HPF_shift, (M, N)))  # high frequency

        # Set scaling factors and add
        gamma1 = gamma_1
        gamma2 = gamma_2
        img_adjusting = gamma1 * img_LF[0:rows, 0:cols] + gamma2 * img_HF[0:rows, 0:cols]

        # Anti-log then rescale to [0,1]
        img_exp = np.expm1(img_adjusting)  # exp(x) + 1
        img_exp = (img_exp - np.min(img_exp)) / (np.max(img_exp) - np.min(img_exp))
        img_out = np.array(255 * img_exp, dtype='uint8')

        # Convert image to YUV to RGB
        img_YUV[:, :, 0] = img_out
        result = cv2.cvtColor(img_YUV, cv2.COLOR_YUV2BGR)

        return result

    def lightness_gray(self, img, gamma_1=0.3, gamma_2=1.5, threshold=65):
        def imclearborder(imgBW, radius):
            # Given a black and white image, first find all of its contours
            imgBWcopy = imgBW.copy()
            contours, hierarchy = cv2.findContours(imgBWcopy.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

            # Get dimensions of image
            imgRows = imgBW.shape[0]
            imgCols = imgBW.shape[1]

            contourList = []  # ID list of contours that touch the border

            # For each contour...
            for idx in np.arange(len(contours)):
                # Get the i'th contour
                cnt = contours[idx]

                # Look at each point in the contour
                for pt in cnt:
                    rowCnt = pt[0][1]
                    colCnt = pt[0][0]

                    # If this is within the radius of the border
                    # this contour goes bye bye!
                    check1 = (rowCnt >= 0 and rowCnt < radius) or (rowCnt >= imgRows - 1 - radius and rowCnt < imgRows)
                    check2 = (colCnt >= 0 and colCnt < radius) or (colCnt >= imgCols - 1 - radius and colCnt < imgCols)

                    if check1 or check2:
                        contourList.append(idx)
                        break

            for idx in contourList:
                cv2.drawContours(imgBWcopy, contours, idx, (0, 0, 0), -1)

            return imgBWcopy

        def bwareaopen(imgBW, areaPixels):
            # Given a black and white image, first find all of its contours
            imgBWcopy = imgBW.copy()
            contours, hierarchy = cv2.findContours(imgBWcopy.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

            # For each contour, determine its total occupying area
            for idx in np.arange(len(contours)):
                area = cv2.contourArea(contours[idx])
                if (area >= 0 and area <= areaPixels):
                    cv2.drawContours(imgBWcopy, contours, idx, (0, 0, 0), -1)

            return imgBWcopy

        # Number of rows and columns
        rows = img.shape[0]
        cols = img.shape[1]

        # Remove some columns from the beginning and end
        img = img[:, 59:cols - 20]

        # Number of rows and columns
        rows = img.shape[0]
        cols = img.shape[1]

        # Convert image to 0 to 1, then do log(1 + I)
        imgLog = np.log1p(np.array(img, dtype="float") / 255)

        # Create Gaussian mask of sigma = 10
        M = 2 * rows + 1
        N = 2 * cols + 1
        sigma = 10
        (X, Y) = np.meshgrid(np.linspace(0, N - 1, N), np.linspace(0, M - 1, M))
        centerX = np.ceil(N / 2)
        centerY = np.ceil(M / 2)
        gaussianNumerator = (X - centerX) ** 2 + (Y - centerY) ** 2

        # Low pass and high pass filters
        Hlow = np.exp(-gaussianNumerator / (2 * sigma * sigma))
        Hhigh = 1 - Hlow

        # Move origin of filters so that it's at the top left corner to match with the input image
        HlowShift = scipy.fftpack.ifftshift(Hlow.copy())
        HhighShift = scipy.fftpack.ifftshift(Hhigh.copy())

        # Filter the image and crop
        If = scipy.fftpack.fft2(imgLog.copy(), (M, N))
        Ioutlow = scipy.real(scipy.fftpack.ifft2(If.copy() * HlowShift, (M, N)))
        Iouthigh = scipy.real(scipy.fftpack.ifft2(If.copy() * HhighShift, (M, N)))

        # Set scaling factors and add
        gamma1 = gamma_1
        gamma2 = gamma_2
        Iout = gamma1 * Ioutlow[0:rows, 0:cols] + gamma2 * Iouthigh[0:rows, 0:cols]

        # Anti-log then rescale to [0,1]
        Ihmf = np.expm1(Iout)
        Ihmf = (Ihmf - np.min(Ihmf)) / (np.max(Ihmf) - np.min(Ihmf))
        Ihmf2 = np.array(255 * Ihmf, dtype="uint8")

        # Threshold the image - Anything below intensity 65 gets set to white
        Ithresh = Ihmf2 < threshold
        Ithresh = 255 * Ithresh.astype("uint8")

        # Clear off the border.  Choose a border radius of 5 pixels
        Iclear = imclearborder(Ithresh, 5)

        # Eliminate regions that have areas below 120 pixels
        Iopen = bwareaopen(Iclear, 120)

        return Ihmf2, Ithresh, Iopen


# if __name__ == "__main__":
#     pass
