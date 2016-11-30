FROM kobotoolbox/koboform_base:latest


# Note: Additional environment variables have been set in `Dockerfile.koboform_base`.
ENV KPI_LOGS_DIR=/srv/logs \
    KPI_WHOOSH_DIR=/srv/whoosh \
    GRUNT_BUILD_DIR=/srv/grunt_build \
    GRUNT_FONTS_DIR=/srv/grunt_fonts \
    WEBPACK_STATS_PATH=/srv/webpack-stats.json \
    DJANGO_SETTINGS_MODULE=kobo.settings \
    # The mountpoint of a volume shared with the `nginx` container. Static files will
    #   be copied there.
    NGINX_STATIC_DIR=/srv/static


##########################################
# Install any additional `apt` packages. #
##########################################

COPY ./apt_requirements.txt "${KPI_SRC_DIR}/"
# Only install if the current version of `apt_requirements.txt` differs from the one used in the base image.
RUN if ! diff "${KPI_SRC_DIR}/apt_requirements.txt" /srv/tmp/base_apt_requirements.txt; then \
        apt-get update -qq && \
        apt-get install -qqy $(cat "${KPI_SRC_DIR}/apt_requirements.txt") && \
        apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \ 
    ; fi


###########################
# Re-sync `pip` packages. #
###########################

COPY ./requirements.txt "${KPI_SRC_DIR}/"
# Only install if the current version of `requirements.txt` differs from the one used in the base image.
RUN if ! diff "${KPI_SRC_DIR}/requirements.txt" /srv/tmp/base_requirements.txt; then \
        pip-sync "${KPI_SRC_DIR}/requirements.txt" 1>/dev/null \
    ; fi


##########################################
# Install any additional `npm` packages. #
##########################################

COPY ./package.json "${KPI_SRC_DIR}/"
# Only install if the current version of `package.json` differs from the one used in the base image.
RUN if ! diff "${KPI_SRC_DIR}/package.json" /srv/tmp/base_package.json; then \
        # Try error-prone `npm install` step twice.
        npm install --quiet || npm install --quiet \
    ; fi


##########################################
# Install any additional Bower packages. #
##########################################

COPY ./bower.json ./.bowerrc "${KPI_SRC_DIR}/"
# Only install if the current versions of `bower.json` or `.bowerrc` differ from the ones used in the base image.
RUN if ! diff "${KPI_SRC_DIR}/bower.json" /srv/tmp/base_bower.json && \
            ! diff "${KPI_SRC_DIR}/.bowerrc" /srv/tmp/base_bowerrc; then \
        bower install --quiet --allow-root --config.interactive=false \
    ; fi


######################
# Build client code. #
######################

COPY ./Gruntfile.js ${KPI_SRC_DIR}/
COPY ./webpack* ${KPI_SRC_DIR}/
COPY ./.eslintrc ${KPI_SRC_DIR}/.eslintrc
COPY ./helper/webpack-config.js ${KPI_SRC_DIR}/helper/webpack-config.js
COPY ./test ${KPI_SRC_DIR}/test

COPY ./jsapp ${KPI_SRC_DIR}/jsapp

RUN mkdir "${GRUNT_BUILD_DIR}" && \
    mkdir "${GRUNT_FONTS_DIR}" && \
    ln -s "${GRUNT_BUILD_DIR}" "${KPI_SRC_DIR}/jsapp/compiled" && \
    rm -rf "${KPI_SRC_DIR}/jsapp/fonts" && \
    ln -s "${GRUNT_FONTS_DIR}" "${KPI_SRC_DIR}/jsapp/fonts" && \
    # FIXME: Move `webpack-stats.json` to some build target directory so these ad-hoc workarounds don't continue to accumulate.
    ln -s "${WEBPACK_STATS_PATH}" webpack-stats.json

RUN grunt copy && npm run build-production


###############################################
# Copy over this directory in its current state. #
###############################################

RUN rm -rf "${KPI_SRC_DIR}"
COPY . "${KPI_SRC_DIR}"

# Restore the backed-up package installation directories.
RUN ln -s "${KPI_NODE_PATH}" "${KPI_SRC_DIR}/node_modules" && \
    ln -s "${BOWER_COMPONENTS_DIR}/" "${KPI_SRC_DIR}/jsapp/xlform/components" && \
    ln -s "${GRUNT_BUILD_DIR}" "${KPI_SRC_DIR}/jsapp/compiled" && \
    ln -s "${GRUNT_FONTS_DIR}" "${KPI_SRC_DIR}/jsapp/fonts" && \
    ln -s "${WEBPACK_STATS_PATH}" webpack-stats.json


###########################
# Organize static assets. #
###########################

RUN python manage.py collectstatic --noinput


#####################################
# Retrieve and compile translations #
#####################################

RUN git submodule init && \
    git submodule update && \
    python manage.py compilemessages


#################################################################
# Persist the log directory, email directory, and Whoosh index. #
#################################################################

RUN mkdir -p "${KPI_LOGS_DIR}/" "${KPI_WHOOSH_DIR}/" "${KPI_SRC_DIR}/emails"
VOLUME "${KPI_LOGS_DIR}/" "${KPI_WHOOSH_DIR}/" "${KPI_SRC_DIR}/emails"


#################################################
# Handle runtime tasks and create main process. #
#################################################

# Using `/etc/profile.d/` as a repository for non-hard-coded environment variable overrides.
RUN echo 'source /etc/profile' >> /root/.bashrc

# FIXME: Allow Celery to run as root ...for now.
ENV C_FORCE_ROOT="true"

# Prepare for execution.
RUN ln -s "${KPI_SRC_DIR}/docker/init.bash" /etc/my_init.d/10_init_kpi.bash && \
    rm -rf /etc/service/wsgi && \
    mkdir -p /etc/service/uwsgi && \
    ln -s "${KPI_SRC_DIR}/docker/run_uwsgi.bash" /etc/service/uwsgi/run

EXPOSE 8000
