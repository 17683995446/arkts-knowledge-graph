/**
 * 继承链文件 - 深度 6
 */

import { InheritanceClass5 } from './InheritanceFile5';

export class InheritanceClass6 extends InheritanceClass5 {

    method0() {
        super.method0?.();
        return 'Inheritance 6 result';
    }


    method1() {
        super.method3?.();
        return 'Inheritance 6 result';
    }


    method2() {
        super.method3?.();
        return 'Inheritance 6 result';
    }


    method3() {
        super.method5?.();
        return 'Inheritance 6 result';
    }


    method4() {
        super.method3?.();
        return 'Inheritance 6 result';
    }

}
