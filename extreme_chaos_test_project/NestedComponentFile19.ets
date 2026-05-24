/**
 * 嵌套组件文件 - 深度 19
 */

import { NestedComponent20 } from './NestedComponentFile20';

@Component
export struct NestedComponent19 {

    build() {
        Column() {
            NestedComponent20()
            NestedComponent20()
            NestedComponent20()
        }
    }

}
