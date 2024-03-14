find_package(PkgConfig)

PKG_CHECK_MODULES(PC_GR_FT4222 gnuradio-ft4222)

FIND_PATH(
    GR_FT4222_INCLUDE_DIRS
    NAMES gnuradio/ft4222/api.h
    HINTS $ENV{FT4222_DIR}/include
        ${PC_FT4222_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    GR_FT4222_LIBRARIES
    NAMES gnuradio-ft4222
    HINTS $ENV{FT4222_DIR}/lib
        ${PC_FT4222_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/gnuradio-ft4222Target.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(GR_FT4222 DEFAULT_MSG GR_FT4222_LIBRARIES GR_FT4222_INCLUDE_DIRS)
MARK_AS_ADVANCED(GR_FT4222_LIBRARIES GR_FT4222_INCLUDE_DIRS)
