#
# Copyright (c) 2015-2026 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
from distutils.version import LooseVersion

from nfv_common import debug
from nfv_vim.objects import HOST_NAME
from nfv_vim.objects import HOST_PERSONALITY

DLOG = debug.debug_get_logger("nfv_vim.strategy.kube_upgrade")

KUBELET_MINOR_SKEW_TOLERANCE = 3


# TODO(vgluzrom): Remove pylint disable once the mixin members (apply_phase, _state,
# report_build_failure, nfvi_kube_upgrade, etc.) are declared in an abstract base class
# that KubeUpgradeStages can inherit from
class KubeUpgradeStages:  # pylint: disable=no-member
    """Mixin containing shared Kubernetes Upgrade logic.

    Requires the class to also inherit from SwUpdateStrategy or similar
    and provide 'kube_to_version' property.
    """

    @property
    def kube_to_version(self):
        raise NotImplementedError(
            "Classes using KubeUpgradeStages must implement kube_to_version"
        )

    @staticmethod
    def get_first_host():
        """This corresponds to the first host that should be updated.

        In simplex env, first host: controller-0. In duplex env: controller-1.
        """
        from nfv_vim import tables

        controller_0_host = None
        controller_1_host = None
        host_table = tables.tables_get_host_table()
        for host in host_table.get_by_personality(HOST_PERSONALITY.CONTROLLER):
            if HOST_NAME.CONTROLLER_0 == host.name:
                controller_0_host = host
            if HOST_NAME.CONTROLLER_1 == host.name:
                controller_1_host = host
        if controller_1_host is None:
            # simplex
            return controller_0_host
        # duplex
        return controller_1_host

    @staticmethod
    def get_second_host():
        """This corresponds to the second host that should be updated.

        In simplex env, second host: None. In duplex env: controller-0.
        """
        from nfv_vim import tables

        controller_0_host = None
        controller_1_host = None
        host_table = tables.tables_get_host_table()
        for host in host_table.get_by_personality(HOST_PERSONALITY.CONTROLLER):
            if HOST_NAME.CONTROLLER_0 == host.name:
                controller_0_host = host
            if HOST_NAME.CONTROLLER_1 == host.name:
                controller_1_host = host
        if controller_1_host is None:
            # simplex
            return None
        # duplex
        return controller_0_host

    def _is_combined_strategy(self):
        return getattr(self, "_kube_upgrade_version", None)

    def _get_kube_version_steps(self, target_version, kube_list):
        """Returns an ordered list for a multi-version kubernetes upgrade.

        Returns an ordered list of kubernetes versions to complete the upgrade
         If the target is already the active version, the list will be empty
        Raises an exception if the kubernetes chain is broken

        This function is called both at the beginning of an upgrade
        (where the starting version is 'active') and during mid-upgrade
        resume/retry (where the starting version may be 'partial').
        """
        # convert the kube_list into a dictionary indexed by version
        kube_dict = {}
        for kube in kube_list:
            kube_dict[kube["kube_version"]] = kube

        # Populate the kube_sequence
        # Start with the target version and traverse based on the
        # 'upgrade_from' field.
        # The loop ends when we reach the active/partial version
        # The loop always inserts at the 'front' of the kube_sequence
        # Only the highest patch version per minor is added to the sequence.
        kube_sequence = []
        ver = target_version
        loop_count = 0
        while True:
            # We should never encounter a version that is not in the dict
            kube = kube_dict.get(ver)
            if kube is None:
                # We do not raise an exception. if the lowest version is
                # 'partial' its 'upgrade_from' will not exist in the dict,
                # so we can stop iterating
                break

            # We do not add the 'active' version to the front of the list
            # since it will not be updated
            if kube["state"] == "active":
                # active means we are at the end of the sequence
                break

            # Only add this version if a higher patch of the same minor
            # is not already in the sequence (i.e., keep only the highest
            # patch per minor version).
            ver_parsed = LooseVersion(ver).version[1:3]  # [major, minor]
            if not kube_sequence or tuple(
                LooseVersion(kube_sequence[0]).version[1:3]
            ) != tuple(ver_parsed):
                kube_sequence.insert(0, ver)

            # 'partial' means we have started updating that version
            # There can be two partial states if the control plane
            # was updated, but the kubelet was not, so add  only the first
            if kube["state"] == "partial":
                # if its partial there is no need for another loop
                break

            # Select the next version to traverse from 'upgrade_from'.
            # Priority: if the active or partial (currently running) version
            # is listed in upgrade_from, pick it directly — the loop will
            # terminate on the next iteration when it sees that state.
            # This handles the case where higher patches of the same minor
            # are installed but not yet active (e.g., active=v1.42.1 but
            # v1.42.3 also exists). Without this check, the traversal would
            # pick v1.42.3 and never converge back to the active version.
            # Otherwise, pick the highest patch from the previous minor.
            target_minor = (ver_parsed[0], ver_parsed[1] - 1)
            active_or_partial = None
            for v in kube["upgrade_from"]:
                if kube_dict.get(v, {}).get("state") in ("active", "partial"):
                    active_or_partial = v
                    break
            if active_or_partial:
                ver = active_or_partial
            else:
                candidates = []
                for v in kube["upgrade_from"]:
                    if tuple(LooseVersion(v).version[1:3]) == target_minor:
                        candidates.append(v)
                if candidates:
                    ver = max(candidates, key=LooseVersion)
                else:
                    ver = kube["upgrade_from"][0]

            # go around the loop again...

            # We should NEVER get into an infinite loop, but if the kube-version entries
            # in sysinv are malformed, we do not want to spin forever
            loop_count += 1
            if loop_count > 10:
                raise Exception("Invalid kubernetes dependency chain detected")

        return kube_sequence

    def _kubelet_map(self):
        """Map the host kubelet versions by the host uuid.

        Leave the kubelet version empty, if the status is not None,
        since that means the kubelet may not be running the version
        indicated.  ie: upgrading-kubelet-failed.
        """
        from nfv_vim import nfvi

        kubelet_map = {}
        for host in self.nfvi_kube_host_upgrade_list:
            # host status can be None if the activity has not been started,
            # or has been completed, in both cases the host version is correct.
            # for the other three states (upgrading, upgraded, failed) only
            # the upgraded state indicates the accurate kubelet version
            if (
                host.status is None
                or host.status
                == nfvi.objects.v1.KUBE_HOST_UPGRADE_STATE.KUBE_HOST_UPGRADED_KUBELET
            ):
                kubelet_map[host.host_uuid] = host.kubelet_version
        return kubelet_map

    def _kubeadm_map(self):
        """Map the host kubeadm versions by the host uuid."""

        kubeadm_map = {}
        for host in self.nfvi_kube_host_upgrade_list:
            kubeadm_map[host.host_uuid] = host.control_plane_version
        return kubeadm_map

    def _query_already_upgraded_hosts(self, kube_ver):
        from nfv_vim import tables

        host_table = tables.tables_get_host_table()
        kubelet_map = self._kubelet_map()

        already_upgraded_hosts = []
        for host in list(host_table.values()):
            if kubelet_map.get(host.uuid) == self.kube_to_version:
                DLOG.info("Host %s kubelet already up to date" % host.name)
                already_upgraded_hosts.append(host)
                continue
            if kubelet_map.get(host.uuid) == kube_ver:
                DLOG.info("Host %s kubelet already at interim version" % host.name)
                already_upgraded_hosts.append(host)
                continue

        return already_upgraded_hosts

    def _add_kube_upgrade_start_stage(self):
        """Add upgrade start strategy stage

        This stage only occurs when no kube upgrade has been initiated.
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_START)
        stage.add_step(strategy.KubeUpgradeStartStep(self.kube_to_version, force=True))
        self.apply_phase.add_stage(stage)
        # Add the stage that comes after the kube upgrade start stage
        self._add_kube_upgrade_download_images_stage()

    def _add_kube_upgrade_download_images_stage(self):
        """Add downloading images stage

        This stage only occurs when kube upgrade has been started.
        It then proceeds to the next stage.
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_DOWNLOAD_IMAGES
        )
        stage.add_step(strategy.KubeUpgradeDownloadImagesStep())
        self.apply_phase.add_stage(stage)
        # Next stage after download images is pre application update
        self._add_kube_pre_application_update_stage()

    def _add_kube_pre_application_update_stage(self):
        """Add kube pre application update stage.

        This stage only occurs after download images
        It then proceeds to the next stage.
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_PRE_APPLICATION_UPDATE
        )
        stage.add_step(strategy.KubePreApplicationUpdateStep())
        self.apply_phase.add_stage(stage)

        # Next stage after pre application update is upgrade networking
        self._add_kube_upgrade_networking_stage()

    def _add_kube_upgrade_networking_stage(self):
        """Add kube upgrade networking stage.

        This stage only occurs after download images
        It then proceeds to the next stage.
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_NETWORKING, False
        )
        stage.add_step(strategy.KubeUpgradeNetworkingStep())
        self.apply_phase.add_stage(stage)

        # Next stage after networking is upgrade storage
        self._add_kube_upgrade_storage_stage()

    def _add_kube_upgrade_storage_stage(self):
        """Add kube upgrade storage stage.

        This stage only occurs after upgrade networking
        It then proceeds to the next stage.
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_STORAGE
        )
        stage.add_step(strategy.KubeUpgradeStorageStep())
        self.apply_phase.add_stage(stage)

        # Next stage after networking is cordon
        self._add_kube_host_cordon_stage()

    def _add_kube_host_cordon_stage(self):
        """Add host cordon stage for a host.

        This will only run if:
        - Host is simplex
        - The combined software + kube upgrade is not running
        """

        from nfv_vim import nfvi
        from nfv_vim import strategy

        first_host = self.get_first_host()
        second_host = self.get_second_host()
        is_simplex = second_host is None
        if is_simplex and not self._is_combined_strategy():
            # todo(abailey): add rollback support to trigger uncordon
            stage = strategy.StrategyStage(
                strategy.STRATEGY_STAGE_NAME.KUBE_HOST_CORDON
            )
            stage.add_step(
                strategy.KubeHostCordonStep(
                    first_host,
                    self.kube_to_version,
                    False,  # force
                    nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_HOST_CORDON_COMPLETE,
                    nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_HOST_CORDON_FAILED,
                )
            )
            self.apply_phase.add_stage(stage)
        self._add_kube_update_stages()

    def _kubelet_version_skew(self, kubeadm_version, kubelet_version):
        """Calculate integer skew between kubeadm (control-plane) minor

        version and kubelet minor version.

        Reference: https://kubernetes.io/releases/version-skew-policy/
        kubelet may be up to three minor versions older than kube-apiserver.

        This routine transforms major.minor.patch version string 'X.Y.Z'
        to scaled representation 100*int(X) + int(Y). The major version is
        scaled by 100. This ensures that major version changes go beyond
        the skew limit. The patch version is ignored.

        :param kubeadm_version: control-plane K8S version
        :param kubelet_version: kubelet K8S version

        :return: integer: skew between kubeadm minor version
                 and kubelet minor version
        """

        def safe_strip(input_string):
            if not input_string:
                return ""
            return "".join(c for c in input_string if c in "1234567890.")

        if any(value is None for value in (kubeadm_version, kubelet_version)):
            raise ValueError("Invalid kubelet version skew input")

        # Split major.minor.patch into integer components
        try:
            kubeadm_map = list(map(int, safe_strip(kubeadm_version).split(".")[:2]))
            kubelet_map = list(map(int, safe_strip(kubelet_version).split(".")[:2]))
        except Exception as e:
            DLOG.error(
                "_kubelet_version_skew: Unexpected error: %s, "
                "kubeadm_version=%s, kubelet_version=%s"
                % (e, kubeadm_version, kubelet_version)
            )
            raise ValueError("Invalid kubelet version skew input")

        if len(kubeadm_map) != 2 or len(kubelet_map) != 2:
            raise ValueError("Invalid kubelet version skew input")

        # Calculate integer skew between kubeadm and kubelet minor version
        skew = 100 * (kubeadm_map[0] - kubelet_map[0]) + (
            kubeadm_map[1] - kubelet_map[1]
        )
        return skew

    def _add_kube_update_stages(self):
        """Stages for control plane, kubelet and cordon."""

        # Algorithm
        # -------------------------
        # Simplex:
        # - loop over kube versions
        #   - control plane
        #   - kubelet: if exceeded skew, or last version
        # -------------------------
        # Duplex:
        # - loop over kube versions
        #   - first control plane
        #   - second control plane
        #   - kubelets: if exceeded skew, or last version
        # -------------------------
        from nfv_vim import strategy

        first_host = self.get_first_host()
        second_host = self.get_second_host()
        ver_list = self._get_kube_version_steps(
            self.kube_to_version, self._nfvi_kube_versions_list
        )
        kubeadm_map = self._kubeadm_map()
        kubelet_map = self._kubelet_map()
        kubelet_min_version = min(kubelet_map.values(), key=LooseVersion, default=None)

        # convert the kube_list into a dictionary indexed by version
        kube_dict = {}
        for kube in self._nfvi_kube_versions_list:
            kube_dict[kube["kube_version"]] = kube

        # Determine whether we have to upgrade control-plane at the
        # first kube version in the upgrade list, otherwise skip.
        skip_first = False
        skip_second = False

        # Kubernetes skew policy allows upgrade of control-plane(s)
        # multiple times before updating kubelet. This logic is aligned
        # with the semantic in sysinv/api/controllers/v1/host.py
        # kube_upgrade_control_plane().

        first_ver = None
        if first_host is not None:
            first_ver = kubeadm_map.get(first_host.uuid)
        second_ver = None
        if second_host is not None:
            second_ver = kubeadm_map.get(second_host.uuid)

        # determine if control-plane already upgraded at this step
        ver_init = ver_list[0] if ver_list else None
        if first_ver == ver_init:
            skip_first = True
        if second_ver == ver_init:
            skip_second = True

        # detect duplex and order
        if len(set(kubeadm_map.values())) != 1:
            if (first_ver is not None) and all(
                LooseVersion(first_ver) > LooseVersion(ver)
                for ver in kubeadm_map.values()
            ):
                # first_host control-plane newer than second
                skip_first = True
            if (second_ver is not None) and all(
                LooseVersion(second_ver) > LooseVersion(ver)
                for ver in kubeadm_map.values()
            ):
                # second_host control-plane newer than first
                skip_second = True

        # initial list of kubelet_stage versions considered for upgrade
        if ver_list:
            upgrade_from = kube_dict[ver_init]["upgrade_from"][0]
            if kubelet_min_version is not None and LooseVersion(
                kubelet_min_version
            ) < LooseVersion(upgrade_from):
                kubelet_stage = [kubelet_min_version]
            else:
                kubelet_stage = [upgrade_from]

            # Upgrade kubelet first if nodes are partially upgraded and one node
            # has exceeded kubelet version skew.
            # Example:  If current kubelet is at 1.29, current kubeadm is at 1.32.
            kubeadm_version = ver_init
            kubelet_version = kubelet_stage[0]
            kubelet_skew = self._kubelet_version_skew(kubeadm_version, kubelet_version)

            # upgrade kubelet if we exceed skew tolerance.
            # When _kube_upgrade_version is set, this is a combined sw-upgrade strategy
            # Kubelet upgrades are deferred to unlock after sw-deploy
            if (
                kubelet_skew >= KUBELET_MINOR_SKEW_TOLERANCE
                and not self._is_combined_strategy()
            ):
                self._add_kube_upgrade_kubelets_stage(ver_init)

                # initialize next iteration
                kubelet_stage = [kubeadm_version]
        else:
            kubelet_stage = []

        for kube_ver in ver_list:
            DLOG.info("Examining %s " % kube_ver)

            # first control plane
            if skip_first:
                # skip only occurs on the first loop
                skip_first = False
            else:
                self._add_kube_upgrade_first_control_plane_stage(first_host, kube_ver)

            # second control plane
            if skip_second:
                skip_second = False
            else:
                self._add_kube_upgrade_second_control_plane_stage(second_host, kube_ver)

            # Evaluate Kubernetes Skew Policy; this will evaluate kubelet version skew
            # for each K8S node. This prevents unsupported advancement of control-plane
            # if any nodes are not current enough.
            # Example:  If current kubelet is at 1.29, current kubeadm is at 1.32,
            # then the minor version skew is 3 (i.e., 32 - 29). We prevent the kubeadm
            # upgrade to 1.33 since the resulting upgrade would have skew of 4.

            # keep kubelet versions we have yet to upgrade
            kubeadm_version = kube_ver
            kubelet_stage.append(kubeadm_version)
            kubelet_version = kubelet_stage[0]
            kubelet_skew = self._kubelet_version_skew(kubeadm_version, kubelet_version)

            # upgrade kubelet if we exceed skew tolerance
            # When _kube_upgrade_version is set, this is a combined sw-upgrade strategy
            # Kubelet upgrades are deferred to unlock after sw-deploy
            if (
                kubelet_skew >= KUBELET_MINOR_SKEW_TOLERANCE
                and not self._is_combined_strategy()
            ):
                self._add_kube_upgrade_kubelets_stage(kube_ver)

                # initialize next iteration
                kubelet_stage = [kubeadm_version]

            # kubelets can 'fail' the build. Return abruptly if it does
            # todo(abailey): change this once all lock/unlock are removed from kubelet
            if self._state == strategy.STRATEGY_STATE.BUILD_FAILED:
                return

        # When _kube_upgrade_version is set, this is a combined sw-upgrade strategy
        # Kubelet upgrades are deferred to unlock after sw-deploy
        if self._is_combined_strategy():
            return

        # Update kubelet to the final version if it isn't already
        if kubelet_stage:
            kubelet_version = kubelet_stage[0]
            kube_ver = kubelet_stage[-1]
            if kubelet_version != self.kube_to_version:
                self._add_kube_upgrade_kubelets_stage(kube_ver)
                if self._state == strategy.STRATEGY_STATE.BUILD_FAILED:
                    return
        else:
            # Ensure worker hosts are unlocked if they are already at the
            # target kubelet version. This handles the case where the
            # upgrade strategy was aborted/recreated, leaving workers locked
            # even though no kubelet upgrade stage is generated for them.
            # Although AIO hosts also have the worker personality, this
            # block should not be reachable with a locked controller
            locked_workers = []
            already_upgraded_hosts = self._query_already_upgraded_hosts(
                self.kube_to_version
            )
            for host in already_upgraded_hosts:
                if (
                    HOST_PERSONALITY.WORKER in host.personality
                    and kubelet_map.get(host.uuid) == self.kube_to_version
                    and host.is_locked()
                ):
                    locked_workers.append(host)

            if locked_workers:
                stage = strategy.StrategyStage(
                    strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_UNLOCK_LOCKED_WORKERS
                )
                stage.add_step(strategy.UnlockHostsStep(locked_workers))
                stage.add_step(strategy.SystemStabilizeStep())
                self.apply_phase.add_stage(stage)

        self._add_kube_host_uncordon_stage()

    def _add_kube_host_uncordon_stage(self):
        """Add host uncordon stage for a host."""

        # simplex only

        from nfv_vim import nfvi
        from nfv_vim import strategy

        first_host = self.get_first_host()
        second_host = self.get_second_host()
        is_simplex = second_host is None
        if is_simplex:
            stage = strategy.StrategyStage(
                strategy.STRATEGY_STAGE_NAME.KUBE_HOST_UNCORDON
            )
            stage.add_step(
                strategy.KubeHostUncordonStep(
                    first_host,
                    self.kube_to_version,
                    False,  # force
                    nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_HOST_UNCORDON_COMPLETE,
                    nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_HOST_UNCORDON_FAILED,
                )
            )
            self.apply_phase.add_stage(stage)
        # after this loop is kube upgrade complete stage
        self._add_kube_upgrade_complete_stage()

    def _add_kube_upgrade_first_control_plane_stage(self, first_host, kube_ver):
        """Add first controller control plane kube upgrade stage."""

        from nfv_vim import nfvi
        from nfv_vim import strategy

        stage_name = "%s %s" % (
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_FIRST_CONTROL_PLANE,
            kube_ver,
        )
        stage = strategy.StrategyStage(stage_name)
        first_host = self.get_first_host()
        # force argument is ignored by control plane API
        force = True
        stage.add_step(
            strategy.KubeHostUpgradeControlPlaneStep(
                first_host,
                kube_ver,
                force,
                nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADED_FIRST_MASTER,
                nfvi.objects.v1.KUBE_UPGRADE_STATE.KUBE_UPGRADING_FIRST_MASTER_FAILED,
            )
        )
        self.apply_phase.add_stage(stage)
        return True

    def _add_kube_upgrade_second_control_plane_stage(self, second_host, kube_ver):
        """Add second control plane kube upgrade stage

        This stage only occurs after networking and if this is a duplex.
        It then proceeds to the next stage.
        """
        from nfv_vim import nfvi
        from nfv_vim import strategy

        objects_v1 = nfvi.objects.v1.KUBE_UPGRADE_STATE

        if second_host is not None:
            # force argument is ignored by control plane API
            force = True
            stage_name = "%s %s" % (
                strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_SECOND_CONTROL_PLANE,
                kube_ver,
            )
            stage = strategy.StrategyStage(stage_name)
            stage.add_step(
                strategy.KubeHostUpgradeControlPlaneStep(
                    second_host,
                    kube_ver,
                    force,
                    objects_v1.KUBE_UPGRADED_SECOND_MASTER,
                    objects_v1.KUBE_UPGRADING_SECOND_MASTER_FAILED,
                )
            )
            self.apply_phase.add_stage(stage)
            return True
        return False

    def _add_kube_upgrade_kubelets_stage(self, kube_ver):
        # todo(abailey): This can be completely redone when lock
        # and unlock are completely obsoleted

        from nfv_vim import tables

        host_table = tables.tables_get_host_table()

        # controller_0 and controller_1 are lists of no more than 1
        # if the controller is AIO it is added to the workers list
        # otherwise it is the std list
        controller_0_std = []
        controller_1_std = []
        controller_0_workers = []
        controller_1_workers = []
        worker_hosts = []
        kubelet_map = self._kubelet_map()

        # Skip hosts that the kubelet is already the correct version
        # group the hosts by their type (controller, storage, worker)
        # place each controller in a separate list
        # there are no kubelets running on storage nodes
        for host in list(host_table.values()):
            if kubelet_map.get(host.uuid) == self.kube_to_version:
                DLOG.info("Host %s kubelet already up to date" % host.name)
                continue
            if kubelet_map.get(host.uuid) == kube_ver:
                DLOG.info("Host %s kubelet already at interim version" % host.name)
                continue
            if HOST_PERSONALITY.CONTROLLER in host.personality:
                if HOST_NAME.CONTROLLER_0 == host.name:
                    if HOST_PERSONALITY.WORKER in host.personality:
                        controller_0_workers.append(host)
                    else:
                        controller_0_std.append(host)
                elif HOST_NAME.CONTROLLER_1 == host.name:
                    if HOST_PERSONALITY.WORKER in host.personality:
                        controller_1_workers.append(host)
                    else:
                        controller_1_std.append(host)
                else:
                    DLOG.warn("Unsupported controller name %s" % host.name)
            elif HOST_PERSONALITY.WORKER in host.personality:
                worker_hosts.append(host)
            else:
                DLOG.info("No kubelet stage required for host %s" % host.name)

        # kubelet order is: controller-1, controller-0 then workers
        # storage nodes can be skipped
        # we only include 'reboot' in a duplex env (includes workers)
        reboot_default = not self._single_controller  # We do NOT reboot an AIO-SX host
        HOST_STAGES = [
            (
                self._add_kubelet_controller_strategy_stages,
                controller_1_std,
                reboot_default,
            ),
            (
                self._add_kubelet_controller_strategy_stages,
                controller_0_std,
                reboot_default,
            ),
            (
                self._add_kubelet_worker_strategy_stages,
                controller_1_workers,
                reboot_default,
            ),
            (
                self._add_kubelet_worker_strategy_stages,
                controller_0_workers,
                reboot_default,
            ),
            (self._add_kubelet_worker_strategy_stages, worker_hosts, reboot_default),
        ]
        stage_name = "kube-upgrade-kubelet %s" % kube_ver
        for add_kubelet_stages_function, host_list, reboot in HOST_STAGES:
            if host_list:
                sorted_host_list = sorted(host_list, key=lambda host: host.name)
                success, reason = add_kubelet_stages_function(
                    sorted_host_list, kube_ver, reboot, stage_name
                )
                # todo(abailey): We need revisit if this can never fail
                if not success:
                    self.report_build_failure(reason)
                    return

    def _add_kube_upgrade_complete_stage(self):
        """Add kube upgrade complete strategy stage

        This stage occurs after all kubelets are upgraded.
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_COMPLETE, False
        )
        stage.add_step(strategy.KubeUpgradeCompleteStep())
        self.apply_phase.add_stage(stage)
        # Next stage after upgrade complete is post application update
        self._add_kube_post_application_update_stage()

    def _add_kube_post_application_update_stage(self):
        """Add kube post application update stage.

        This stage occurs after the upgrade is completed
        It then proceeds to the next stage.
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_POST_APPLICATION_UPDATE, False
        )
        stage.add_step(strategy.KubePostApplicationUpdateStep())
        self.apply_phase.add_stage(stage)

        # Next stage after post application update is upgrade cleanup
        self._add_kube_upgrade_cleanup_stage()

    def _add_kube_upgrade_cleanup_stage(self):
        """kube upgrade cleanup stage deletes the kube upgrade.

        This stage occurs after the post application update stage.
        """
        from nfv_vim import strategy

        stage = strategy.StrategyStage(
            strategy.STRATEGY_STAGE_NAME.KUBE_UPGRADE_CLEANUP, False
        )
        stage.add_step(strategy.KubeUpgradeCleanupStep())
        self.apply_phase.add_stage(stage)

    def _build_kube_upgrade_stages(self):
        """Builds the Kubernetes Upgrade stages based on the current state.

        Handles both fresh starts and resuming from a specific state.
        """
        from nfv_vim import nfvi

        objects_v1 = nfvi.objects.v1.KUBE_UPGRADE_STATE

        RESUME_STATE = {
            objects_v1.KUBE_UPGRADE_STARTED: (
                self._add_kube_upgrade_download_images_stage
            ),
            objects_v1.KUBE_UPGRADE_DOWNLOADING_IMAGES_FAILED: (
                self._add_kube_upgrade_download_images_stage
            ),
            objects_v1.KUBE_UPGRADE_DOWNLOADED_IMAGES: (
                self._add_kube_pre_application_update_stage
            ),
            objects_v1.KUBE_PRE_UPDATING_APPS_FAILED: (
                self._add_kube_pre_application_update_stage
            ),
            objects_v1.KUBE_PRE_UPDATED_APPS: (self._add_kube_upgrade_networking_stage),
            objects_v1.KUBE_UPGRADING_NETWORKING_FAILED: (
                self._add_kube_upgrade_networking_stage
            ),
            objects_v1.KUBE_UPGRADED_NETWORKING: (self._add_kube_upgrade_storage_stage),
            objects_v1.KUBE_UPGRADING_STORAGE_FAILED: (
                self._add_kube_upgrade_storage_stage
            ),
            objects_v1.KUBE_UPGRADED_STORAGE: (self._add_kube_host_cordon_stage),
            objects_v1.KUBE_HOST_CORDON_FAILED: (self._add_kube_host_cordon_stage),
            objects_v1.KUBE_HOST_CORDON_COMPLETE: (self._add_kube_update_stages),
            objects_v1.KUBE_UPGRADING_FIRST_MASTER_FAILED: (
                self._add_kube_update_stages
            ),
            objects_v1.KUBE_UPGRADED_FIRST_MASTER: (self._add_kube_update_stages),
            objects_v1.KUBE_UPGRADING_SECOND_MASTER_FAILED: (
                self._add_kube_update_stages
            ),
            objects_v1.KUBE_UPGRADED_SECOND_MASTER: (self._add_kube_update_stages),
            objects_v1.KUBE_UPGRADING_KUBELETS: (self._add_kube_update_stages),
            objects_v1.KUBE_HOST_UNCORDON_FAILED: (self._add_kube_host_uncordon_stage),
            objects_v1.KUBE_HOST_UNCORDON_COMPLETE: (
                self._add_kube_upgrade_complete_stage
            ),
            objects_v1.KUBE_UPGRADE_COMPLETE: (
                self._add_kube_post_application_update_stage
            ),
            objects_v1.KUBE_POST_UPDATING_APPS_FAILED: (
                self._add_kube_post_application_update_stage
            ),
            objects_v1.KUBE_POST_UPDATED_APPS: (self._add_kube_upgrade_cleanup_stage),
        }

        matching_version_upgraded = False
        for kube_version_object in self.nfvi_kube_versions_list:
            if kube_version_object["kube_version"] == self.kube_to_version:
                matching_version_upgraded = (
                    kube_version_object["target"]
                    and kube_version_object["state"] == "active"
                )
                break
        else:
            DLOG.warn(
                "Invalid to_version(%s) for the kube upgrade" % self.kube_to_version
            )
            self.report_build_failure(
                "Invalid to_version value: '%s'" % self.kube_to_version
            )
            return

        if self._nfvi_alarms:
            alarm_id_set = set()
            for alarm_data in self._nfvi_alarms:
                alarm_id_set.add(alarm_data["alarm_id"])
            alarm_id_list = ", ".join(sorted(alarm_id_set))
            DLOG.warn(
                "Cannot upgrade kube: Active alarms present [ %s ]" % alarm_id_list
            )
            self.report_build_failure("active alarms present [ %s ]" % alarm_id_list)
            return

        if self.nfvi_kube_upgrade is None:
            if matching_version_upgraded:
                self.report_build_failure(
                    "Kubernetes is already upgraded to: %s" % self.kube_to_version
                )
                return
            self._add_kube_upgrade_start_stage()
        else:
            current_state = self.nfvi_kube_upgrade.state
            resume_from_stage = RESUME_STATE.get(current_state)
            if resume_from_stage is None:
                self.report_build_failure(
                    "Unable to resume kube upgrade from state: %s" % current_state
                )
                return
            resume_from_stage()
