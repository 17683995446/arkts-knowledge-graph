/**
 * 循环导入文件 C
 */

import { CircularA } from './CircularA';

export class CircularC {
    useA() {
        return new CircularA();
    }
}
